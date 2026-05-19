from pydantic import BaseModel


class HistoryItem(BaseModel):
    role: str
    content: str


class ChatTaskPayload(BaseModel):
    task_id: str
    session_id: int
    user_message: str
    history: list[HistoryItem] = []


class ChatTaskResult(BaseModel):
    task_id: str
    answer: str
