from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession, MessageRole


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(self, user_id: int, title: str = "새 대화") -> ChatSession:
        chat = ChatSession(user_id=user_id, title=title)
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def get_sessions(self, user_id: int) -> list[ChatSession]:
        stmt = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_session(self, session_id: UUID | str, user_id: int) -> ChatSession | None:
        stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_message(self, session_id: UUID | str, role: MessageRole, content: str) -> ChatMessage:
        msg = ChatMessage(session_id=session_id, role=role.value, content=content)
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg

    async def get_messages(self, session_id: UUID | str, limit: int = 50) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def touch_session(self, session_id: UUID | str) -> None:
        stmt = update(ChatSession).where(ChatSession.id == session_id).values(updated_at=datetime.now(UTC))
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_message_feedback(
        self, message_id: int, session_id: UUID | str, feedback: str
    ) -> ChatMessage | None:
        stmt = select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.session_id == session_id,
        )
        result = await self.session.execute(stmt)
        msg = result.scalar_one_or_none()
        if msg:
            msg.feedback = feedback
            await self.session.commit()
            await self.session.refresh(msg)
        return msg

    async def delete_session(self, session_id: UUID | str) -> None:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        session = result.scalar_one_or_none()
        if session:
            await self.session.delete(session)
            await self.session.commit()

    async def update_title(self, session_id: UUID | str, title: str) -> None:
        stmt = update(ChatSession).where(ChatSession.id == session_id).values(title=title)
        await self.session.execute(stmt)
        await self.session.commit()
