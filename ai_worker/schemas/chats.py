from pydantic import BaseModel


class HistoryItem(BaseModel):
    role: str
    content: str


class HealthProfilePayload(BaseModel):
    primary_conditions: list[str] = []
    allergies: list[str] = []
    current_medications: list[str] = []
    lifestyle_exercise: str = ""
    lifestyle_smoking: bool | None = None
    lifestyle_alcohol: str = ""


class ChatTaskPayload(BaseModel):
    task_id: str
    session_id: int
    user_message: str
    history: list[HistoryItem] = []
    health_profile: HealthProfilePayload | None = None
    stream: bool = False


class ChatTaskResult(BaseModel):
    task_id: str
    answer: str
    title: str | None = None
