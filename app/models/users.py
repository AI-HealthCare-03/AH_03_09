from datetime import datetime

from pydantic import BaseModel


class User(BaseModel):
    id: str
    kakao_id: str
    email: str | None = None
    nickname: str
    profile_image: str | None = None
    created_at: datetime | None = None
