from enum import StrEnum

from tortoise import fields, models


class ExerciseHabit(StrEnum):
    REGULAR = "REGULAR"
    IRREGULAR = "IRREGULAR"
    NONE = "NONE"


class AlcoholHabit(StrEnum):
    NONE = "NONE"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"


class ProfileChangedBy(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    ADMIN = "ADMIN"


class HealthProfile(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="health_profile",
        on_delete=fields.CASCADE,
        unique=True,
    )
    primary_conditions = fields.JSONField(default=list)
    allergies = fields.JSONField(default=list)
    current_medications = fields.JSONField(default=list)
    lifestyle_exercise = fields.CharEnumField(enum_type=ExerciseHabit, default=ExerciseHabit.NONE)
    lifestyle_smoking = fields.BooleanField(default=False)
    lifestyle_alcohol = fields.CharEnumField(enum_type=AlcoholHabit, default=AlcoholHabit.NONE)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "health_profiles"


class HealthProfileHistory(models.Model):
    id = fields.BigIntField(primary_key=True)
    health_profile = fields.ForeignKeyField(
        "models.HealthProfile",
        related_name="history",
        on_delete=fields.CASCADE,
    )
    snapshot = fields.JSONField()
    changed_by = fields.CharEnumField(enum_type=ProfileChangedBy)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "health_profile_histories"
