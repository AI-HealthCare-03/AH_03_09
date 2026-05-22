import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import BIGINT, Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models.ocr.base import Base


class OcrStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class DocType(StrEnum):
    PRESCRIPTION = "PRESCRIPTION"
    DRUG_BAG = "DRUG_BAG"
    OTHER = "OTHER"


class MetricType(StrEnum):
    OCR_ACCURACY = "OCR_ACCURACY"
    PARSE_ACCURACY = "PARSE_ACCURACY"
    LATENCY = "LATENCY"


class OcrDocument(Base):
    __tablename__ = "ocr_documents"

    record_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    doc_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ocr_status: Mapped[str] = mapped_column(String(20), nullable=False, default=OcrStatus.PENDING)
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    result: Mapped["OcrResult | None"] = relationship("OcrResult", back_populates="document", uselist=False)
    medications: Mapped[list["Medication"]] = relationship("Medication", back_populates="document")
    disease_codes: Mapped[list["DiseaseCode"]] = relationship("DiseaseCode", back_populates="document")
    corrections: Mapped[list["OcrCorrection"]] = relationship("OcrCorrection", back_populates="document")
    metrics: Mapped[list["AiPerformanceMetric"]] = relationship("AiPerformanceMetric", back_populates="document")


class OcrResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("ocr_documents.record_id", ondelete="CASCADE"), nullable=False
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    clova_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_user_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    document: Mapped["OcrDocument"] = relationship("OcrDocument", back_populates="result")


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("ocr_documents.record_id", ondelete="CASCADE"), nullable=False
    )
    medication_name: Mapped[str] = mapped_column(String(200), nullable=False)
    edi_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    generic_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timing: Mapped[str | None] = mapped_column(String(100), nullable=True)
    usage_time: Mapped[str | None] = mapped_column(String(200), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_of_day: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    document: Mapped["OcrDocument"] = relationship("OcrDocument", back_populates="medications")


class DiseaseCode(Base):
    __tablename__ = "disease_codes"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("ocr_documents.record_id", ondelete="CASCADE"), nullable=False
    )
    icd10_code: Mapped[str] = mapped_column(String(20), nullable=False)
    disease_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped["OcrDocument"] = relationship("OcrDocument", back_populates="disease_codes")


class OcrCorrection(Base):
    __tablename__ = "ocr_corrections"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey("ocr_documents.record_id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(BIGINT, nullable=True)
    original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_by: Mapped[int] = mapped_column(BIGINT, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped["OcrDocument"] = relationship("OcrDocument", back_populates="corrections")


class AiPerformanceMetric(Base):
    __tablename__ = "ai_performance_metrics"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    document_id: Mapped[int | None] = mapped_column(
        BIGINT, ForeignKey("ocr_documents.record_id", ondelete="SET NULL"), nullable=True
    )
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_value: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    baseline_value: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    preprocessing_applied: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    measured_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    additional_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    document: Mapped["OcrDocument | None"] = relationship("OcrDocument", back_populates="metrics")
