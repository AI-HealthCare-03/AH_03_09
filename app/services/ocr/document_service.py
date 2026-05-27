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
from app.dtos.ocr.document_dtos import OcrDocumentUpdateRequest
from app.models.ocr.ocr_document import OcrDocument, OcrStatus
from app.repositories.ocr.document_repository import OcrDocumentRepository
from app.services.ocr.s3_service import LOCAL_BUCKET, S3Service

logger = logging.getLogger(__name__)


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
        await self.session.flush()
        return doc

    async def reanalyze_document(self, record_id: int, user_id: int) -> OcrDocument:
        doc = await self.get_document(record_id, user_id)
        if doc.ocr_status == OcrStatus.DONE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="이미 처리 완료된 문서는 재추출할 수 없습니다."
            )
        if doc.ocr_status == OcrStatus.PROCESSING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="처리 중인 문서는 재추출할 수 없습니다.")
        if doc.reanalyze_count >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="재추출 횟수를 초과했습니다. 파일에 문제가 있을 수 있으니 새로운 파일로 재업로드해 주세요.",
            )
        doc.ocr_status = OcrStatus.PENDING
        doc.reanalyze_count += 1
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
            from app.dtos.guides import GenerateGuideRequest, GuideType
            from app.services.guides import GuideService

            medication_names = [m.medication_name for m in (doc.medications or []) if m.medication_name]
            guide_req = GenerateGuideRequest(
                patient_id=str(user_id),
                guide_types=list(GuideType),
                medication_names=medication_names,
            )
            guide_resp = await GuideService().create_guide_job(guide_req)
            guide_job_id = guide_resp.job_id

        if trigger_chatbot_context:
            logger.info(
                "trigger_chatbot_context: REQ-OCR-018 pgvector 임베딩 미구현, 건너뜀 (record_id=%s)",
                doc.record_id,
            )

        return doc.record_id, doc.job_id, guide_job_id

    async def _publish_ocr_job(self, doc: OcrDocument) -> None:
        payload = {
            "job_id": str(doc.job_id),
            "record_id": doc.record_id,
            "s3_key": doc.s3_key,
            "s3_bucket": doc.s3_bucket,
            "user_id": doc.user_id,
            "mime_type": doc.mime_type,
            "original_filename": doc.original_filename,
        }
        try:
            redis = self._redis or await get_redis()
            await redis.publish(f"ocr:request:{doc.job_id}", json.dumps(payload))
        except Exception as exc:
            logger.error("Failed to publish OCR job (job_id=%s): %s", doc.job_id, exc)
