import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.dtos.base import BaseSerializerModel

# ── Response schemas ──────────────────────────────────────────────────────────


class MedicationResponse(BaseSerializerModel):
    id: int
    medication_name: str
    edi_code: str | None = None
    generic_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    timing: str | None = None
    duration_days: int | None = None
    time_of_day: list | None = None
    instructions: str | None = None
    warnings: list | None = None
    confidence_score: float | None = None
    is_confirmed: bool
    is_active: bool


class DiseaseCodeResponse(BaseSerializerModel):
    id: int
    icd10_code: str
    disease_name: str | None = None
    confidence_score: float | None = None
    is_confirmed: bool
    is_active: bool


class OcrResultResponse(BaseSerializerModel):
    id: int
    raw_text: str | None = None
    processed_text: str | None = None
    confidence_score: float | None = None
    processing_time_ms: int | None = None
    is_user_edited: bool
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class OcrDocumentResponse(BaseSerializerModel):
    record_id: int
    job_id: uuid.UUID
    original_filename: str
    doc_type: str | None = None
    ocr_status: str
    issued_date: date | None = None
    valid_until: date | None = None
    hospital_name: str | None = None
    thumbnail_url: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OcrDocumentDetailResponse(OcrDocumentResponse):
    medications: list[MedicationResponse] = []
    disease_codes: list[DiseaseCodeResponse] = []
    result: OcrResultResponse | None = None


class OcrDocumentListResponse(BaseSerializerModel):
    documents: list[OcrDocumentResponse]
    total: int


class UploadedFileItem(BaseSerializerModel):
    record_id: int
    job_id: uuid.UUID
    ocr_status: str
    original_filename: str


class OcrUploadResponse(BaseSerializerModel):
    uploaded_files: list[UploadedFileItem]
    message: str = "업로드가 완료되었습니다. OCR 처리가 시작됩니다."


class OcrJobStatusResponse(BaseSerializerModel):
    job_id: uuid.UUID
    record_id: int
    status: str
    progress_pct: int = 0
    message: str | None = None
    result_url: str | None = None
    estimated_remaining_seconds: int | None = None


class OcrPreviewResponse(BaseSerializerModel):
    filename: str
    file_size: int
    mime_type: str
    is_valid: bool
    message: str


# ── Request schemas ───────────────────────────────────────────────────────────


class OcrDocumentUpdateRequest(BaseModel):
    doc_type: str | None = None
    issued_date: date | None = None
    valid_until: date | None = None
    hospital_name: str | None = None


class MedicationUpdateRequest(BaseModel):
    medication_name: str | None = None
    edi_code: str | None = None
    generic_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    timing: str | None = None
    duration_days: int | None = None
    time_of_day: list | None = None
    instructions: str | None = None
    warnings: list | None = None


class DiseaseCodeUpdateRequest(BaseModel):
    icd10_code: str | None = None
    disease_name: str | None = None


class OcrResultUpdateRequest(BaseModel):
    processed_text: str
