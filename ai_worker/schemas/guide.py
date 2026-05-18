from pydantic import BaseModel


class GuideJobPayload(BaseModel):
    job_id: str
    patient_id: str
    guide_types: list[str]  # GuideType enum 값 문자열 배열
