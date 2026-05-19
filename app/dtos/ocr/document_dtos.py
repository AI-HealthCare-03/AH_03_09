import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.dtos.base import BaseSerializerModel

# ── Response schemas ──────────────────────────────────────────────────────────


class MedicationResponse(BaseSerializerModel):
    id: int
    medication_name: str
    generic_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    timing: str | None = None
    duration_days: int | None = None
    time_of_day: dict | None = None
    instructions: str | None = None
    warnings: list | None = None
    confidence_score: float | None = None
    is_confirmed: bool
    is_active: bool


class DiseaseCodeResponse(BaseSerializerModel):
    id: int
    icd10_code: str
    disease_name: str | None = None
    is_primary: bool
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


class OcrUploadResponse(BaseSerializerModel):
    record_id: int
    job_id: uuid.UUID
    ocr_status: str
    message: str = "업로드 완료. OCR 처리가 시작됩니다."


class OcrJobStatusResponse(BaseSerializerModel):
    job_id: uuid.UUID
    record_id: int
    ocr_status: str
    processing_time_ms: int | None = None
    error_message: str | None = None


# ── Request schemas ───────────────────────────────────────────────────────────


class OcrDocumentUpdateRequest(BaseModel):
    doc_type: str | None = None
    issued_date: date | None = None
    valid_until: date | None = None
    hospital_name: str | None = None


class MedicationUpdateRequest(BaseModel):
    medication_name: str | None = None
    generic_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    timing: str | None = None
    duration_days: int | None = None
    time_of_day: dict | None = None
    instructions: str | None = None
    warnings: list | None = None


class DiseaseCodeUpdateRequest(BaseModel):
    icd10_code: str | None = None
    disease_name: str | None = None
    is_primary: bool | None = None


class OcrResultUpdateRequest(BaseModel):
    processed_text: str
