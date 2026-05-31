from datetime import datetime
from typing import Literal
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
    feedback: str | None = None
    created_at: datetime


class MessageFeedbackRequest(BaseModel):
    feedback: Literal["good", "bad"]


class ChatMessageListResponse(BaseModel):
    messages: list[ChatMessageResponse]


class ChatMessageSendRequest(BaseModel):
    content: str = Field(..., min_length=1, description="유저가 보낼 메시지")
    guide_id: str | None = Field(default=None, description="연동할 가이드 ID (OCR→가이드→챗봇 흐름)")


class ChatSendMessageResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


class ChatSessionDetailResponse(BaseModel):
    id: UUID
    title: str
    messages: list[ChatMessageResponse]
    created_at: datetime
    updated_at: datetime


class WebSocketOutMessage(BaseModel):
    type: str  # "stream" | "done" | "error"
    content: str
