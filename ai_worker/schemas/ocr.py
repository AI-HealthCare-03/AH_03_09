import uuid

from pydantic import BaseModel


class OcrTaskPayload(BaseModel):
    job_id: uuid.UUID
    record_id: int
    s3_key: str
    s3_bucket: str
    user_id: uuid.UUID
    mime_type: str
    original_filename: str
