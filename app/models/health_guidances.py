from enum import StrEnum

from tortoise import fields, models


class GuidanceType(StrEnum):
    MEDICATION_GUIDE = "MEDICATION_GUIDE"
    LIFESTYLE_GUIDE = "LIFESTYLE_GUIDE"
    DIETARY_GUIDE = "DIETARY_GUIDE"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FLAGGED = "FLAGGED"


class HealthGuidance(models.Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField()
    health_profile = fields.ForeignKeyField(
        "models.HealthProfile",
        related_name="guidances",
        on_delete=fields.SET_NULL,
        null=True,
    )
    guidance_type = fields.CharEnumField(enum_type=GuidanceType)
    content = fields.TextField()
    ai_confidence = fields.FloatField(null=True)
    requires_expert_review = fields.BooleanField(default=False)
    verification_status = fields.CharEnumField(
        enum_type=VerificationStatus,
        default=VerificationStatus.PENDING,
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "health_guidances"
