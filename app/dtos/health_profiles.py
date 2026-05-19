from datetime import datetime

from pydantic import BaseModel

from app.dtos.base import BaseSerializerModel
from app.models.health_profiles import AlcoholHabit, ExerciseHabit, ProfileChangedBy


class HealthProfileUpdateRequest(BaseModel):
    primary_conditions: list[str] | None = None
    allergies: list[str] | None = None
    current_medications: list[str] | None = None
    lifestyle_exercise: ExerciseHabit | None = None
    lifestyle_smoking: bool | None = None
    lifestyle_alcohol: AlcoholHabit | None = None


class HealthProfileResponse(BaseSerializerModel):
    id: int
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
