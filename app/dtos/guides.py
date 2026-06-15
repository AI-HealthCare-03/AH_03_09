from enum import StrEnum

from pydantic import BaseModel, Field


class GuideType(StrEnum):
    MEDICATION = "MEDICATION"
    LIFESTYLE = "LIFESTYLE"
    DIET = "DIET"
    EXERCISE = "EXERCISE"


class JobStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class GuideGenerationStatus(StrEnum):
    DONE = "DONE"
    SKIPPED = "SKIPPED"


class GuideSkipReason(StrEnum):
    NO_MEDICATION_INFO = "NO_MEDICATION_INFO"
    NO_DISEASE_INFO = "NO_DISEASE_INFO"
    LOW_CONFIDENCE_OCR = "LOW_CONFIDENCE_OCR"
    DRUG_NOT_FOUND = "DRUG_NOT_FOUND"


class MedicationMatchStatus(StrEnum):
    EXACT_DB_MATCH = "EXACT_DB_MATCH"
    WEB_REFERENCE = "WEB_REFERENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    SIMILAR_MATCH = "SIMILAR_MATCH"
    NOT_FOUND = "NOT_FOUND"


# ── 요청 스키마 ──────────────────────────────────────────────────────────────


class MedicationDetail(BaseModel):
    medication_name: str
    generic_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    timing: str | None = None
    duration_days: int | None = None
    time_of_day: list | None = None
    warnings: list | None = None


class GenerateGuideRequest(BaseModel):
    patient_id: str
    guide_types: list[GuideType]
    medication_names: list[str] = Field(default_factory=list)
    medications: list[MedicationDetail] = Field(default_factory=list)
    disease_codes: list[str] = Field(default_factory=list)
    disease_names: list[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    rating_comprehension: int = Field(ge=1, le=5)
    rating_usefulness: int = Field(ge=1, le=5)
    rating_safety: int = Field(ge=1, le=5)
    comment: str | None = None


class UpdateFeedbackStatusRequest(BaseModel):
    status: str  # "submitted"


# ── 가이드 생성 결과 모델 ─────────────────────────────────────────────────────


class GuideGenerationResult(BaseModel):
    guide_type: GuideType
    status: GuideGenerationStatus
    skip_reason: GuideSkipReason | None = None


# ── 가이드 섹션 내부 모델 ──────────────────────────────────────────────────────


class MedicationItem(BaseModel):
    name: str
    dosage: str
    timing: str
    before_after_meal: str
    side_effects: list[str]
    cautions: list[str]
    easy_summary: list[str] = []
    missed_dose: str
    storage: str
    action_icons: list[dict] = []
    usage_icons: list[dict] = []
    match_status: MedicationMatchStatus | None = None
    disclaimer: str | None = None
    source_name: str | None = None


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
    generation_results: list[GuideGenerationResult] | None = None


class GuideListItem(BaseModel):
    guide_id: str
    created_at: str
    guide_types: list[GuideType]
    medication_names: list[str] = Field(default_factory=list)
    disease_names: list[str] = Field(default_factory=list)


class GuideListResponse(BaseModel):
    items: list[GuideListItem]
    total: int


class FeedbackResponse(BaseModel):
    feedback_id: str
    created_at: str


class FeedbackStatusResponse(BaseModel):
    is_submitted: bool
    rating_comprehension: int | None = None
    rating_usefulness: int | None = None
    comment: str | None = None


class GuideContextResponse(BaseModel):
    guide_id: str
    medications: list[str]
    schedule: list[dict]
    key_instructions: list[str]
    disease_codes: list[str]
    disease_names: list[str] = Field(default_factory=list)
    drug_details: list[dict] = Field(default_factory=list)
