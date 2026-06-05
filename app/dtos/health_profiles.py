from datetime import date, datetime

from pydantic import BaseModel

from app.dtos.base import BaseSerializerModel
from app.models.health_profiles import AlcoholHabit, ExerciseHabit, GenderType, ProfileChangedBy


class HealthProfileUpdateRequest(BaseModel):
    gender: GenderType | None = None
    birth_date: date | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    blood_pressure_systolic: int | None = None
    blood_pressure_diastolic: int | None = None
    primary_conditions: list[str] | None = None
    allergies: list[str] | None = None
    current_medications: list[str] | None = None
    lifestyle_exercise: ExerciseHabit | None = None
    lifestyle_smoking: bool | None = None
    lifestyle_alcohol: AlcoholHabit | None = None


class HealthProfileResponse(BaseSerializerModel):
    id: int
    gender: GenderType | None
    birth_date: date | None
    height_cm: int | None
    weight_kg: int | None
    blood_pressure_systolic: int | None
    blood_pressure_diastolic: int | None
    primary_conditions: list
    allergies: list
    current_medications: list
    lifestyle_exercise: ExerciseHabit
    lifestyle_smoking: bool
    lifestyle_alcohol: AlcoholHabit
    updated_at: datetime


class HealthProfileHistoryResponse(BaseSerializerModel):
    id: int
    snapshot: dict
    changed_by: ProfileChangedBy
    created_at: datetime
