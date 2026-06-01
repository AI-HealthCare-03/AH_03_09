import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.sqlalchemy_client import get_async_session
from app.dependencies.security import get_request_user
from app.dtos.ocr.document_dtos import (
    DiseaseCodeResponse,
    DiseaseCodeUpdateRequest,
    DrugSearchResult,
    MedicationCreateRequest,
    MedicationResponse,
    MedicationUpdateRequest,
    OcrConfirmRequest,
    OcrConfirmResponse,
    OcrDocumentDetailResponse,
    OcrDocumentListResponse,
    OcrDocumentResponse,
    OcrDocumentUpdateRequest,
    OcrJobStatusResponse,
    OcrPreviewResponse,
    OcrResultResponse,
    OcrResultUpdateRequest,
    OcrUploadResponse,
    UploadedFileItem,
)
from app.models.ocr.ocr_document import DocType, OcrStatus
from app.models.users import User
from app.services.ocr.document_service import OcrDocumentService
from app.services.ocr.file_validator import validate_file_count, validate_upload

ocr_router = APIRouter(prefix="/ocr", tags=["ocr"])

_AUTH = Annotated[User, Depends(get_request_user)]
_SESSION = Annotated[AsyncSession, Depends(get_async_session)]


# ── Utility ───────────────────────────────────────────────────────────────────


@ocr_router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# ── Drug search ───────────────────────────────────────────────────────────────


@ocr_router.get("/drugs/search", response_model=list[DrugSearchResult])
async def search_drugs(
    q: Annotated[str, Query(min_length=1, max_length=100)],
    current_user: _AUTH,  # noqa: ARG001
    session: _SESSION,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> list[DrugSearchResult]:
    """약물명 검색 (drug_master ILIKE + word_similarity 랭킹)"""
    q = q.strip()
    if len(q) < 2:
        return []
    rows = await session.execute(
        text(
            "SELECT item_name FROM drug_master"
            " WHERE item_name ILIKE :pattern"
            " ORDER BY word_similarity(:q, item_name) DESC, length(item_name)"
            " LIMIT :limit"
        ),
        {"q": q, "pattern": f"%{q}%", "limit": limit},
    )
    return [DrugSearchResult(item_name=row[0]) for row in rows.fetchall()]


# ── Upload & Preview ──────────────────────────────────────────────────────────


@ocr_router.post(
    "/upload",
    response_model=OcrUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["files"],
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {"type": "string", "format": "binary"},
                                "description": "처방전·약봉투 파일 (최대 5개, JPEG·PNG·PDF)",
                            }
                        },
                    }
                }
            },
            "required": True,
        }
    },
)
async def upload_documents(
    current_user: _AUTH,
    session: _SESSION,
    files: Annotated[list[UploadFile], File(description="처방전·약봉투 파일 (최대 5개, JPEG·PNG·PDF)")],
) -> OcrUploadResponse:
    """처방전·약봉투 파일을 S3에 업로드하고 OCR 처리 작업을 생성합니다. (REQ-OCR-002/003)"""
    validate_file_count(files)

    # 파일 유효성 검사를 DB 호출보다 먼저 수행
    file_contents: list[tuple[UploadFile, bytes]] = []
    for file in files:
        content = await validate_upload(file)
        file_contents.append((file, content))

    svc = OcrDocumentService(session)

    daily_limit = 20
    today_count = await svc.repo.count_today_uploads(current_user.id)
    if today_count + len(files) > daily_limit:
        remaining = max(0, daily_limit - today_count)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": f"일일 업로드 한도({daily_limit}건)를 초과했습니다. 오늘 {today_count}건 업로드하셨으며 {remaining}건 더 업로드 가능합니다.",
                "today_count": today_count,
                "daily_limit": daily_limit,
                "remaining": remaining,
            },
        )

    uploaded: list[UploadedFileItem] = []
    for file, content in file_contents:
        doc = await svc.upload_document(
            user_id=current_user.id,
            filename=file.filename or "upload",
            mime_type=file.content_type,  # type: ignore[arg-type]
            content=content,
        )
        uploaded.append(
            UploadedFileItem(
                record_id=doc.record_id,
                job_id=doc.job_id,
                ocr_status=doc.ocr_status,
                original_filename=doc.original_filename,
            )
        )

    return OcrUploadResponse(uploaded_files=uploaded)


@ocr_router.post("/preview", response_model=OcrPreviewResponse, status_code=status.HTTP_200_OK)
async def preview_file(
    current_user: _AUTH,  # noqa: ARG001
    file: UploadFile,
) -> OcrPreviewResponse:
    """파일을 DB·S3 저장 없이 유효성만 검사합니다. (REQ-OCR-003)"""
    try:
        content = await validate_upload(file)
        return OcrPreviewResponse(
            filename=file.filename or "",
            file_size=len(content),
            mime_type=file.content_type or "",
            is_valid=True,
            message="업로드 가능한 파일입니다.",
        )
    except HTTPException as exc:
        return OcrPreviewResponse(
            filename=file.filename or "",
            file_size=0,
            mime_type=file.content_type or "",
            is_valid=False,
            message=str(exc.detail),
        )


# ── Job status ────────────────────────────────────────────────────────────────


@ocr_router.get("/jobs/{job_id}/status", response_model=OcrJobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    current_user: _AUTH,
    session: _SESSION,
) -> OcrJobStatusResponse:
    """비동기 OCR 처리 상태를 조회합니다. (REQ-OCR-004)"""
    svc = OcrDocumentService(session)
    doc = await svc.get_job_status(job_id, current_user.id)

    ocr_status = doc.ocr_status
    progress_pct = {"PENDING": 0, "PROCESSING": 50, "DONE": 100, "FAILED": 0}.get(ocr_status, 0)
    message_map = {
        "PENDING": "OCR 처리 대기 중입니다.",
        "PROCESSING": "OCR 처리 중입니다.",
        "DONE": "OCR 처리가 완료되었습니다.",
        "FAILED": "OCR 처리에 실패했습니다.",
    }

    retake_recommended = False
    if ocr_status == "DONE" and doc.result is not None:
        score = doc.result.confidence_score
        if score is not None and score < 0.7:
            retake_recommended = True
            message_map["DONE"] = (
                "OCR 처리가 완료되었으나 이미지 품질이 낮습니다. 더 선명하게 재촬영하시면 정확도가 높아집니다."
            )

    return OcrJobStatusResponse(
        job_id=doc.job_id,
        record_id=doc.record_id,
        status=ocr_status,
        progress_pct=progress_pct,
        message=message_map.get(ocr_status),
        result_url=None,
        estimated_remaining_seconds=None,
        reanalyze_count=doc.reanalyze_count,
        retake_recommended=retake_recommended,
    )


@ocr_router.post("/jobs/{job_id}/confirm", response_model=OcrConfirmResponse, status_code=status.HTTP_200_OK)
async def confirm_ocr(
    job_id: uuid.UUID,
    body: OcrConfirmRequest,
    current_user: _AUTH,
    session: _SESSION,
) -> OcrConfirmResponse:
    """OCR 결과를 확인하고 가이드 생성·챗봇 컨텍스트 등록을 트리거합니다."""
    svc = OcrDocumentService(session)
    record_id, doc_job_id, guide_job_id = await svc.confirm_document(
        job_id, current_user.id, body.trigger_guide, body.trigger_chatbot_context
    )
    return OcrConfirmResponse(record_id=record_id, job_id=doc_job_id, guide_job_id=guide_job_id)


# ── OCR Records ───────────────────────────────────────────────────────────────


@ocr_router.get("/records", response_model=OcrDocumentListResponse)
async def list_records(
    current_user: _AUTH,
    session: _SESSION,
    doc_type: Annotated[DocType | None, Query()] = None,
    ocr_status: Annotated[OcrStatus | None, Query()] = None,
    sort: Annotated[str, Query()] = "created_at_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> OcrDocumentListResponse:
    """사용자의 OCR 처리 결과 목록을 조회합니다. (REQ-OCR-007)"""
    svc = OcrDocumentService(session)
    docs, total = await svc.list_documents(
        current_user.id,
        doc_type=doc_type,
        ocr_status=ocr_status,
        sort=sort,
        page=page,
        size=size,
    )
    return OcrDocumentListResponse(
        documents=[
            OcrDocumentResponse.model_validate(d).model_copy(
                update={
                    "low_confidence": d.result is not None
                    and d.result.confidence_score is not None
                    and d.result.confidence_score < 0.7
                }
            )
            for d in docs
        ],
        total=total,
    )


@ocr_router.get("/records/{record_id}", response_model=OcrDocumentDetailResponse)
async def get_record(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> OcrDocumentDetailResponse:
    """특정 OCR 처리 결과의 상세 정보를 조회합니다. (REQ-OCR-008)"""
    svc = OcrDocumentService(session)
    doc = await svc.get_document(record_id, current_user.id)
    detail = OcrDocumentDetailResponse.model_validate(doc)
    if doc.doc_type != "PRESCRIPTION":
        detail.disease_codes = []
    return detail


@ocr_router.get("/records/{record_id}/file")
async def get_record_file(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> Response:
    """원본 파일(이미지·PDF)을 서빙합니다."""
    svc = OcrDocumentService(session)
    return await svc.get_file_response(record_id, current_user.id)


@ocr_router.patch("/records/{record_id}", response_model=OcrDocumentResponse)
async def update_record(
    record_id: int,
    body: OcrDocumentUpdateRequest,
    current_user: _AUTH,
    session: _SESSION,
) -> OcrDocumentResponse:
    """OCR 문서 메타데이터를 수정합니다."""
    svc = OcrDocumentService(session)
    return await svc.update_document(record_id, current_user.id, body)


@ocr_router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> None:
    """OCR 문서를 소프트 삭제합니다. 30일 후 완전히 삭제됩니다. (REQ-OCR-009)"""
    svc = OcrDocumentService(session)
    await svc.delete_document(record_id, current_user.id)


@ocr_router.post("/records/{record_id}/reanalyze", response_model=OcrJobStatusResponse)
async def reanalyze_record(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
    is_reclassify: Annotated[bool, Query()] = False,
) -> OcrJobStatusResponse:
    """FAILED/DONE 문서를 재추출합니다. PROCESSING 중이면 409. is_reclassify=true이면 재추출 횟수를 소모하지 않습니다."""
    svc = OcrDocumentService(session)
    doc = await svc.reanalyze_document(record_id, current_user.id, is_reclassify=is_reclassify)
    return OcrJobStatusResponse(
        job_id=doc.job_id,
        record_id=doc.record_id,
        status=doc.ocr_status,
        progress_pct=0,
        message="재추출 요청이 접수되었습니다.",
        reanalyze_count=doc.reanalyze_count,
    )


# ── Medications ───────────────────────────────────────────────────────────────


@ocr_router.post(
    "/records/{record_id}/medications",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_medication(
    record_id: int,
    body: MedicationCreateRequest,
    current_user: _AUTH,
    session: _SESSION,
) -> MedicationResponse:
    """약물 항목을 수동으로 추가합니다."""
    svc = OcrDocumentService(session)
    med = await svc.add_medication(record_id, current_user.id, body)
    await session.commit()
    return MedicationResponse.model_validate(med)


@ocr_router.get("/records/{record_id}/medications", response_model=list[MedicationResponse])
async def list_medications(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> list[MedicationResponse]:
    """처방전의 약물 목록을 조회합니다. (REQ-OCR-010)"""
    svc = OcrDocumentService(session)
    doc = await svc.get_document(record_id, current_user.id)
    return [MedicationResponse.model_validate(m) for m in doc.medications if m.is_active]


@ocr_router.patch("/records/{record_id}/medications/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    record_id: int,
    medication_id: int,
    body: MedicationUpdateRequest,
    current_user: _AUTH,
    session: _SESSION,
) -> MedicationResponse:
    """약물 정보를 수정합니다. (REQ-OCR-013)"""
    svc = OcrDocumentService(session)
    med = await svc.update_medication(record_id, medication_id, current_user.id, body)
    await session.commit()
    return MedicationResponse.model_validate(med)


@ocr_router.delete("/records/{record_id}/medications/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    record_id: int,
    medication_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> None:
    """약물 항목을 소프트 삭제합니다."""
    svc = OcrDocumentService(session)
    await svc.delete_medication(record_id, medication_id, current_user.id)
    await session.commit()


@ocr_router.post("/records/{record_id}/medications/confirm", status_code=status.HTTP_200_OK)
async def confirm_medications(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> dict[str, int]:
    """약물 목록 전체를 확인 처리합니다. (REQ-OCR-017)"""
    svc = OcrDocumentService(session)
    confirmed_count = await svc.confirm_medications(record_id, current_user.id)
    await session.commit()
    return {"confirmed_count": confirmed_count}


@ocr_router.delete("/records/{record_id}/medications/confirm", status_code=status.HTTP_200_OK)
async def unconfirm_medications(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> dict[str, int]:
    """약물 목록 전체 확인을 해제합니다."""
    svc = OcrDocumentService(session)
    unconfirmed_count = await svc.unconfirm_medications(record_id, current_user.id)
    await session.commit()
    return {"unconfirmed_count": unconfirmed_count}


# ── Disease Codes ─────────────────────────────────────────────────────────────


@ocr_router.get("/records/{record_id}/disease-codes", response_model=list[DiseaseCodeResponse])
async def list_disease_codes(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> list[DiseaseCodeResponse]:
    """처방전의 질병 분류기호 목록을 조회합니다. (REQ-OCR-011)"""
    svc = OcrDocumentService(session)
    doc = await svc.get_document(record_id, current_user.id)
    if doc.doc_type != "PRESCRIPTION":
        return []
    return [DiseaseCodeResponse.model_validate(c) for c in doc.disease_codes if c.is_active]


@ocr_router.patch("/records/{record_id}/disease-codes/{disease_code_id}", response_model=DiseaseCodeResponse)
async def update_disease_code(
    record_id: int,
    disease_code_id: int,
    body: DiseaseCodeUpdateRequest,
    current_user: _AUTH,
    session: _SESSION,
) -> DiseaseCodeResponse:
    """ICD-10 코드를 수정합니다. 질병명은 코드 기반으로 자동 갱신됩니다. (REQ-OCR-014)"""
    if not body.icd10_code:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="icd10_code는 필수입니다.")
    svc = OcrDocumentService(session)
    code = await svc.update_disease_code(record_id, disease_code_id, current_user.id, body.icd10_code)
    return DiseaseCodeResponse.model_validate(code)


@ocr_router.post("/records/{record_id}/disease-codes/confirm", status_code=status.HTTP_200_OK)
async def confirm_disease_codes(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> dict[str, int]:
    """질병 분류기호 전체를 확인 처리합니다. (REQ-OCR-017)"""
    svc = OcrDocumentService(session)
    confirmed_count = await svc.confirm_disease_codes(record_id, current_user.id)
    await session.commit()
    return {"confirmed_count": confirmed_count}


@ocr_router.delete("/records/{record_id}/disease-codes/confirm", status_code=status.HTTP_200_OK)
async def unconfirm_disease_codes(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> dict[str, int]:
    """질병 분류기호 전체 확인을 해제합니다."""
    svc = OcrDocumentService(session)
    unconfirmed_count = await svc.unconfirm_disease_codes(record_id, current_user.id)
    await session.commit()
    return {"unconfirmed_count": unconfirmed_count}


# ── OCR Result ────────────────────────────────────────────────────────────────


@ocr_router.get("/records/{record_id}/result", response_model=OcrResultResponse)
async def get_ocr_result(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> OcrResultResponse:
    """OCR 원본 처리 결과를 조회합니다. (REQ-OCR-012)"""
    svc = OcrDocumentService(session)
    doc = await svc.get_document(record_id, current_user.id)
    if doc.result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR 결과가 아직 없습니다.")
    return OcrResultResponse.model_validate(doc.result)


@ocr_router.patch("/records/{record_id}/result", response_model=OcrResultResponse)
async def update_ocr_result(
    record_id: int,
    body: OcrResultUpdateRequest,
    current_user: _AUTH,
    session: _SESSION,
) -> OcrResultResponse:
    """OCR 텍스트를 사용자가 직접 수정합니다. (REQ-OCR-015)"""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Day 3에서 구현 예정")
