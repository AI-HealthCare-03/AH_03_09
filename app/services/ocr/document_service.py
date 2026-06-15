import json
import logging
import os
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import config
from app.core.redis_client import get_redis
from app.dtos.ocr.document_dtos import MedicationCreateRequest, MedicationUpdateRequest, OcrDocumentUpdateRequest
from app.models.ocr.ocr_document import DiseaseCode, Medication, OcrCorrection, OcrDocument, OcrStatus
from app.repositories.ocr.document_repository import OcrDocumentRepository
from app.services.ocr.s3_service import LOCAL_BUCKET, S3Service

logger = logging.getLogger(__name__)


def _to_list(v: list | str | None) -> list | None:
    if v is None:
        return None
    return v if isinstance(v, list) else [v]


async def _lookup_disease_name(icd10_code: str) -> str | None:
    """ICD-10 코드에 해당하는 한국어 질병명을 GPT-mini로 조회합니다."""
    if not config.OPENAI_API_KEY:
        return None
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    try:
        resp = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": f"ICD-10 코드 {icd10_code}의 한국어 질병명은? 알면 질병명만, 모르면 null만 답하세요.",
                }
            ],
            max_tokens=50,
            temperature=0,
        )
        answer = resp.choices[0].message.content.strip()
        return None if answer.lower() == "null" else answer
    except Exception:
        return None


class OcrDocumentService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis | None = None) -> None:
        self.session = session
        self.repo = OcrDocumentRepository(session)
        self._redis = redis

    async def list_documents(
        self,
        user_id: int,
        doc_type: str | None = None,
        ocr_status: str | None = None,
        sort: str = "created_at_desc",
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[OcrDocument], int]:
        return await self.repo.list_by_user(
            user_id,
            doc_type=doc_type,
            ocr_status=ocr_status,
            sort=sort,
            limit=size,
            offset=(page - 1) * size,
        )

    async def get_document(self, record_id: int, user_id: int) -> OcrDocument:
        doc = await self.repo.get_by_record_id(record_id, user_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
        return doc

    async def get_job_status(self, job_id: uuid.UUID, user_id: int) -> OcrDocument:
        doc = await self.repo.get_by_job_id(job_id, user_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")
        return doc

    async def upload_document(
        self,
        user_id: int,
        filename: str,
        mime_type: str,
        content: bytes,
    ) -> OcrDocument:
        """중복 검사 → S3 업로드 → DB 레코드 생성 → PENDING 반환. (REQ-OCR-002/003)"""
        file_hash = S3Service.compute_hash(content)

        existing = await self.repo.get_by_file_hash(user_id, file_hash)
        if existing is not None:
            if existing.reanalyze_count >= 5 and existing.ocr_status == OcrStatus.FAILED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "처리할 수 없는 파일입니다. 파일에 문제가 있을 수 있으니 다른 파일로 시도해주세요.",
                        "existing_record_id": existing.record_id,
                    },
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "이미 업로드된 파일입니다.",
                    "existing_record_id": existing.record_id,
                },
            )

        s3_svc = S3Service()
        s3_key, _ = await s3_svc.upload(
            content=content,
            user_id=user_id,
            mime_type=mime_type,
            original_filename=filename,
        )

        doc = OcrDocument(
            user_id=user_id,
            original_filename=filename,
            s3_key=s3_key,
            s3_bucket=config.AWS_S3_BUCKET_NAME or LOCAL_BUCKET,
            file_hash=file_hash,
            file_size=len(content),
            mime_type=mime_type,
            ocr_status=OcrStatus.PENDING,
        )
        doc = await self.repo.create(doc)
        await self.session.commit()
        await self.session.refresh(doc)

        await self._publish_ocr_job(doc)

        return doc

    async def delete_document(self, record_id: int, user_id: int) -> None:
        doc = await self.get_document(record_id, user_id)
        if doc.ocr_status == "PROCESSING":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="처리 중인 문서는 삭제할 수 없습니다.")
        doc.is_active = False
        doc.deleted_at = datetime.now(UTC)
        await self.session.commit()

    async def get_file_response(self, record_id: int, user_id: int) -> Response:
        doc = await self.get_document(record_id, user_id)
        if doc.s3_bucket == LOCAL_BUCKET:
            if not os.path.exists(doc.s3_key):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="파일을 찾을 수 없습니다.")
            return FileResponse(doc.s3_key, media_type=doc.mime_type, filename=doc.original_filename)
        url = S3Service().presigned_url(doc.s3_key)
        return RedirectResponse(url)

    async def update_document(self, record_id: int, user_id: int, body: OcrDocumentUpdateRequest) -> OcrDocument:
        doc = await self.get_document(record_id, user_id)
        if body.doc_type is not None:
            doc.doc_type = body.doc_type
        if body.issued_date is not None:
            doc.issued_date = body.issued_date
        if body.valid_until is not None:
            doc.valid_until = body.valid_until
        if body.hospital_name is not None:
            doc.hospital_name = body.hospital_name
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def add_medication(self, record_id: int, user_id: int, body: MedicationCreateRequest) -> Medication:
        doc = await self.get_document(record_id, user_id)
        if doc.ocr_status != OcrStatus.DONE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="OCR 처리가 완료된 문서에만 약물을 추가할 수 있습니다.",
            )
        return await self.repo.add_medication(
            document_id=record_id,
            medication_name=body.medication_name,
            frequency=body.frequency,
            duration_days=body.duration_days,
        )

    async def update_medication(
        self, record_id: int, medication_id: int, user_id: int, body: MedicationUpdateRequest
    ) -> Medication:
        med = await self.repo.get_medication(record_id, medication_id, user_id)
        if med is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="약물 정보를 찾을 수 없습니다.")
        for field, value in body.model_dump(exclude_unset=True).items():
            original = getattr(med, field, None)
            self.session.add(
                OcrCorrection(
                    document_id=record_id,
                    field_name=field,
                    entity_type="medication",
                    entity_id=medication_id,
                    original_value=str(original) if original is not None else None,
                    corrected_value=str(value) if value is not None else None,
                    corrected_by=user_id,
                )
            )
            setattr(med, field, value)
        med.is_confirmed = False
        await self.session.commit()
        await self.session.refresh(med)
        return med

    async def update_disease_code(
        self, record_id: int, disease_code_id: int, user_id: int, icd10_code: str
    ) -> DiseaseCode:
        code = await self.repo.get_disease_code(record_id, disease_code_id, user_id)
        if code is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="질병분류기호를 찾을 수 없습니다.")
        if icd10_code != code.icd10_code:
            self.session.add(
                OcrCorrection(
                    document_id=record_id,
                    field_name="icd10_code",
                    entity_type="disease_code",
                    entity_id=disease_code_id,
                    original_value=code.icd10_code,
                    corrected_value=icd10_code,
                    corrected_by=user_id,
                )
            )
            code.icd10_code = icd10_code
            code.disease_name = await _lookup_disease_name(icd10_code)
        await self.session.commit()
        await self.session.refresh(code)
        return code

    async def delete_medication(self, record_id: int, medication_id: int, user_id: int) -> None:
        med = await self.repo.get_medication(record_id, medication_id, user_id)
        if med is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="약물 정보를 찾을 수 없습니다.")
        med.is_active = False
        await self.session.flush()

    async def confirm_medications(self, record_id: int, user_id: int) -> int:
        """문서의 활성 약물 전체를 is_confirmed=True로 처리합니다."""
        doc = await self.repo.get_by_record_id(record_id, user_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
        return await self.repo.confirm_all_medications(record_id, user_id)

    async def unconfirm_medications(self, record_id: int, user_id: int) -> int:
        """문서의 활성 약물 전체를 is_confirmed=False로 해제합니다."""
        doc = await self.repo.get_by_record_id(record_id, user_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
        return await self.repo.unconfirm_all_medications(record_id, user_id)

    async def confirm_disease_codes(self, record_id: int, user_id: int) -> int:
        """문서의 활성 질병코드 전체를 is_confirmed=True로 처리합니다."""
        doc = await self.repo.get_by_record_id(record_id, user_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
        return await self.repo.confirm_all_disease_codes(record_id, user_id)

    async def unconfirm_disease_codes(self, record_id: int, user_id: int) -> int:
        """문서의 활성 질병코드 전체를 is_confirmed=False로 해제합니다."""
        doc = await self.repo.get_by_record_id(record_id, user_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
        return await self.repo.unconfirm_all_disease_codes(record_id, user_id)

    async def reanalyze_document(self, record_id: int, user_id: int, is_reclassify: bool = False) -> OcrDocument:
        doc = await self.get_document(record_id, user_id)
        if doc.ocr_status == OcrStatus.PROCESSING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="처리 중인 문서는 재추출할 수 없습니다.")
        if not is_reclassify:
            if doc.reanalyze_count >= 5:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="재추출 횟수를 초과했습니다. 파일에 문제가 있을 수 있으니 새로운 파일로 재업로드해 주세요.",
                )
            doc.reanalyze_count += 1
        doc.ocr_status = OcrStatus.PENDING
        await self.session.commit()
        await self.session.refresh(doc)
        await self._publish_ocr_job(doc)
        return doc

    async def confirm_document(
        self,
        job_id: uuid.UUID,
        user_id: int,
        trigger_guide: bool,
        trigger_chatbot_context: bool,
    ) -> tuple[int, uuid.UUID, str | None]:
        """OCR 결과를 확인하고 가이드 생성·챗봇 컨텍스트 등록을 트리거합니다."""
        doc = await self.repo.get_by_job_id_with_medications(job_id, user_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")
        if doc.ocr_status != OcrStatus.DONE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="OCR 처리가 완료된 문서만 확인할 수 있습니다.",
            )

        guide_job_id: str | None = None
        if trigger_guide:
            from app.dtos.guides import GenerateGuideRequest, GuideType, MedicationDetail
            from app.services.guides import GuideService

            meds = [m for m in (doc.medications or []) if m.is_active and m.medication_name]
            codes = [c for c in (doc.disease_codes or []) if c.is_active and c.icd10_code]

            guide_req = GenerateGuideRequest(
                patient_id=str(user_id),
                guide_types=list(GuideType),
                medication_names=[m.medication_name for m in meds],
                medications=[
                    MedicationDetail(
                        medication_name=m.medication_name,
                        generic_name=m.generic_name,
                        dosage=m.dosage,
                        frequency=m.frequency,
                        timing=m.timing,
                        duration_days=m.duration_days,
                        time_of_day=_to_list(m.time_of_day),
                        warnings=_to_list(m.warnings),
                    )
                    for m in meds
                ],
                disease_codes=[c.icd10_code for c in codes],
                disease_names=[c.disease_name or "" for c in codes],
            )
            guide_resp = await GuideService().create_guide_job(guide_req)
            guide_job_id = guide_resp.job_id
            doc.guide_job_id = guide_job_id
            await self.session.commit()

        if trigger_chatbot_context:
            logger.info(
                "trigger_chatbot_context: REQ-OCR-018 pgvector 임베딩 미구현, 건너뜀 (record_id=%s)",
                doc.record_id,
            )

        return doc.record_id, doc.job_id, guide_job_id

    def _merge_multi_doc_data(self, docs: list[OcrDocument]) -> tuple[list[Medication], list[DiseaseCode]]:
        """여러 문서의 약물·질병코드를 중복 제거하여 합산합니다. 앞 문서 우선."""
        seen_meds: set[str] = set()
        merged_meds: list[Medication] = []
        seen_codes: set[str] = set()
        merged_codes: list[DiseaseCode] = []
        for doc in docs:
            for m in doc.medications or []:
                if m.is_active and m.medication_name:
                    key = m.medication_name.strip().lower()
                    if key not in seen_meds:
                        seen_meds.add(key)
                        merged_meds.append(m)
            for c in doc.disease_codes or []:
                if c.is_active and c.icd10_code and c.icd10_code not in seen_codes:
                    seen_codes.add(c.icd10_code)
                    merged_codes.append(c)
        return merged_meds, merged_codes

    async def _publish_ocr_job(self, doc: OcrDocument) -> None:
        payload = {
            "job_id": str(doc.job_id),
            "record_id": doc.record_id,
            "s3_key": doc.s3_key,
            "s3_bucket": doc.s3_bucket,
            "user_id": doc.user_id,
            "mime_type": doc.mime_type,
            "original_filename": doc.original_filename,
            "doc_type_hint": doc.doc_type,
        }
        try:
            redis = self._redis or await get_redis()
            await redis.publish(f"ocr:request:{doc.job_id}", json.dumps(payload))
        except Exception as exc:
            logger.error("Failed to publish OCR job (job_id=%s): %s", doc.job_id, exc)
