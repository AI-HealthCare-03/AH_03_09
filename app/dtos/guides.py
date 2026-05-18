from enum import Enum

from pydantic import BaseModel, Field


class GuideType(str, Enum):
    MEDICATION = "MEDICATION"
    LIFESTYLE = "LIFESTYLE"
    DIET = "DIET"
    EXERCISE = "EXERCISE"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


# ── 요청 스키마 ──────────────────────────────────────────────────────────────

class GenerateGuideRequest(BaseModel):
    patient_id: str
    guide_types: list[GuideType]


class FeedbackRequest(BaseModel):
    rating_comprehension: int = Field(ge=1, le=5)
    rating_usefulness: int = Field(ge=1, le=5)
    rating_safety: int = Field(ge=1, le=5)
    comment: str | None = None


class UpdateFeedbackStatusRequest(BaseModel):
    status: str  # "submitted"


# ── 가이드 섹션 내부 모델 ──────────────────────────────────────────────────────

class MedicationItem(BaseModel):
    name: str
    dosage: str
    timing: str
    before_after_meal: str
    side_effects: list[str]
    cautions: list[str]
    missed_dose: str
    storage: str


class MedicationGuide(BaseModel):
    medications: list[MedicationItem]


class ScheduleEntry(BaseModel):
    time: str
    medications: list[str]


class LifestyleGuide(BaseModel):
    tips: list[str]


class DietGuide(BaseModel):
    forbidden: list[str]
    recommended: list[str]
    hydration: str


class ExerciseGuide(BaseModel):
    intensity: str
    frequency: str
    duration: str
    cautions: list[str]


# ── 응답 스키마 ──────────────────────────────────────────────────────────────

class GenerateGuideResponse(BaseModel):
    job_id: str
    estimated_seconds: int = 10


class GuideStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    guide_id: str | None = None


class GuideResponse(BaseModel):
    guide_id: str
    guide_types: list[GuideType]
    created_at: str
    medication_guide: MedicationGuide | None = None
    schedule_table: list[ScheduleEntry] | None = None
    lifestyle_guide: LifestyleGuide | None = None
    diet_guide: DietGuide | None = None
    exercise_guide: ExerciseGuide | None = None


class FeedbackResponse(BaseModel):
    feedback_id: str
    created_at: str


class FeedbackStatusResponse(BaseModel):
    is_submitted: bool


class GuideContextResponse(BaseModel):
    guide_id: str
    medications: list[str]
    disease_codes: list[str]
    key_instructions: list[str]
