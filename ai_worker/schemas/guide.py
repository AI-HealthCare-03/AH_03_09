from pydantic import BaseModel, Field


class GuideJobPayload(BaseModel):
    job_id: str
    guide_id: str = ""  # FastAPI에서 미리 생성한 UUID; 기존 payload 호환을 위해 기본값 유지
    patient_id: str
    guide_types: list[str] = Field(default_factory=list)  # GuideType enum 값 문자열 배열
    medication_names: list[str] = Field(default_factory=list)
    medications: list[dict] = Field(default_factory=list)  # MedicationDetail을 dict로 직렬화
    disease_codes: list[str] = Field(default_factory=list)
    disease_names: list[str] = Field(default_factory=list)
