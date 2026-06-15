from pydantic import BaseModel


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatTaskPayload(BaseModel):
    session_id: str
    user_message: str
    history: list[HistoryMessage]
    health_profile: dict | None = None
    guides: list[dict] | None = None
    drug_details: list[dict] | None = None
    rag_results: list[dict] | None = None
