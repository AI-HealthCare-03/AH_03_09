from uuid import UUID

from app.models.chat import ChatMessage, ChatSession, MessageRole


class ChatRepository:
    async def create_session(self, user_id: int, title: str = "새 대화") -> ChatSession:
        return await ChatSession.create(user_id=user_id, title=title)

    async def get_sessions(self, user_id: int) -> list[ChatSession]:
        return await ChatSession.filter(user_id=user_id).order_by("-updated_at").all()

    async def get_session(self, session_id: UUID | str, user_id: int) -> ChatSession | None:
        return await ChatSession.filter(id=session_id, user_id=user_id).first()

    async def create_message(self, session_id: UUID | str, role: MessageRole, content: str) -> ChatMessage:
        return await ChatMessage.create(session_id=session_id, role=role, content=content)

    async def get_messages(self, session_id: UUID | str, limit: int = 50) -> list[ChatMessage]:
        return await ChatMessage.filter(session_id=session_id).order_by("created_at").limit(limit).all()

    async def touch_session(self, session_id: UUID | str) -> None:
        await ChatSession.filter(id=session_id).update()
