from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.dtos.base import BaseSerializerModel


class ChatSessionCreateRequest(BaseModel):
    title: str = "새 대화"


class ChatSessionResponse(BaseSerializerModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseSerializerModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    messages: list[ChatMessageResponse]


class ChatMessageSendRequest(BaseModel):
    content: str = Field(..., min_length=1, description="유저가 보낼 메시지")


class ChatSendMessageResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


class WebSocketOutMessage(BaseModel):
    type: str  # "stream" | "done" | "error"
    content: str
