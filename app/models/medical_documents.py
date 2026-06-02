from enum import StrEnum

from tortoise import fields, models


class DocumentType(StrEnum):
    PRESCRIPTION = "PRESCRIPTION"
    MEDICINE_LABEL = "MEDICINE_LABEL"
    DISCHARGE_NOTICE = "DISCHARGE_NOTICE"
    HEALTH_CHECK = "HEALTH_CHECK"


class FileFormat(StrEnum):
    PNG = "PNG"
    JPG = "JPG"
    PDF = "PDF"


class UploadStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class MedicalDocument(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="medical_documents",
        on_delete=fields.CASCADE,
    )
    document_type = fields.CharEnumField(enum_type=DocumentType)
    file_path = fields.CharField(max_length=512)
    file_format = fields.CharEnumField(enum_type=FileFormat)
    file_size = fields.IntField()
    upload_status = fields.CharEnumField(enum_type=UploadStatus, default=UploadStatus.PENDING)
    confidence_score = fields.FloatField(null=True)
    is_verified = fields.BooleanField(default=False)
    processed_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medical_documents"


class OCRResult(models.Model):
    id = fields.BigIntField(primary_key=True)
    document = fields.ForeignKeyField(
        "models.MedicalDocument",
        related_name="ocr_results",
        on_delete=fields.CASCADE,
    )
    extracted_text = fields.TextField()
    structured_data = fields.JSONField()
    important_fields = fields.JSONField()
    masked_pii = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "ocr_results"
