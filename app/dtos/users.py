from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kakao_id: str
    email: str | None = None
    name: str | None = None
    gender: str | None = None
    age_range: str | None = None
    birthday: str | None = None
    birthyear: str | None = None
    phone_number: str | None = None
    created_at: datetime | None = None


class WithdrawRequest(BaseModel):
    confirmation_text: str
