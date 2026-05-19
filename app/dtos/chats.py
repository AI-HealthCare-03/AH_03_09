from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.dtos.base import BaseSerializerModel
from app.models.chats import MessageRole


class ChatSessionCreateRequest(BaseModel):
    title: Annotated[str, Field(default="새 대화", max_length=100)]


class ChatMessageSendRequest(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=2000)]


class ChatMessageResponse(BaseSerializerModel):
    id: int
    role: MessageRole
    content: str
    created_at: datetime


class ChatSessionResponse(BaseSerializerModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionDetailResponse(BaseSerializerModel):
    id: int
    title: str
    messages: list[ChatMessageResponse]
    created_at: datetime
    updated_at: datetime
