import uuid
from enum import StrEnum

from tortoise import fields, models


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatSession(models.Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    user = fields.ForeignKeyField("models.User", related_name="chat_sessions", on_delete=fields.CASCADE)
    title = fields.CharField(max_length=200, default="새 대화")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "chat_sessions"


class ChatMessage(models.Model):
    id = fields.BigIntField(primary_key=True)
    session = fields.ForeignKeyField("models.ChatSession", related_name="messages", on_delete=fields.CASCADE)
    role = fields.CharEnumField(enum_type=MessageRole, max_length=10)
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"
        ordering = ["created_at"]
