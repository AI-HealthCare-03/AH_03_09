import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.sqlalchemy_client import get_async_session
from app.dependencies.security import get_request_user
from app.dtos.ocr.document_dtos import (
    DiseaseCodeResponse,
    DiseaseCodeUpdateRequest,
    MedicationResponse,
    MedicationUpdateRequest,
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
    svc = OcrDocumentService(session)

    uploaded: list[UploadedFileItem] = []
    for file in files:
        content = await validate_upload(file)
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

    return OcrJobStatusResponse(
        job_id=doc.job_id,
        record_id=doc.record_id,
        status=ocr_status,
        progress_pct=progress_pct,
        message=message_map.get(ocr_status),
        result_url=None,
        estimated_remaining_seconds=None,
    )


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
        documents=[OcrDocumentResponse.model_validate(d) for d in docs],
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
    return OcrDocumentDetailResponse.model_validate(doc)


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
    """OCR 문서를 소프트 삭제합니다. (REQ-OCR-009)"""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Day 3에서 구현 예정")


# ── Medications ───────────────────────────────────────────────────────────────


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
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Day 3에서 구현 예정")


@ocr_router.post("/records/{record_id}/medications/confirm", status_code=status.HTTP_200_OK)
async def confirm_medications(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> dict[str, str]:
    """약물 목록 전체를 확인 처리합니다. (REQ-OCR-017)"""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Day 3에서 구현 예정")


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
    return [DiseaseCodeResponse.model_validate(c) for c in doc.disease_codes if c.is_active]


@ocr_router.patch("/records/{record_id}/disease-codes/{disease_code_id}", response_model=DiseaseCodeResponse)
async def update_disease_code(
    record_id: int,
    disease_code_id: int,
    body: DiseaseCodeUpdateRequest,
    current_user: _AUTH,
    session: _SESSION,
) -> DiseaseCodeResponse:
    """질병 분류기호를 수정합니다. (REQ-OCR-014)"""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Day 3에서 구현 예정")


@ocr_router.post("/records/{record_id}/disease-codes/confirm", status_code=status.HTTP_200_OK)
async def confirm_disease_codes(
    record_id: int,
    current_user: _AUTH,
    session: _SESSION,
) -> dict[str, str]:
    """질병 분류기호 전체를 확인 처리합니다. (REQ-OCR-017)"""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Day 3에서 구현 예정")


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
