from app.models.chats import ChatMessage, ChatSession, MessageRole


class ChatSessionRepository:
    def __init__(self):
        self._model = ChatSession

    async def create(self, user_id: int, title: str) -> ChatSession:
        return await self._model.create(user_id=user_id, title=title)

    async def get_by_id_and_user(self, session_id: int, user_id: int) -> ChatSession | None:
        return await self._model.get_or_none(id=session_id, user_id=user_id)

    async def get_all_by_user(self, user_id: int) -> list[ChatSession]:
        return await self._model.filter(user_id=user_id).order_by("-created_at")

    async def update_title(self, session: ChatSession, title: str) -> None:
        session.title = title
        await session.save(update_fields=["title"])

    async def delete(self, session: ChatSession) -> None:
        await session.delete()


class ChatMessageRepository:
    def __init__(self):
        self._model = ChatMessage

    async def create(self, session_id: int, role: MessageRole, content: str) -> ChatMessage:
        return await self._model.create(session_id=session_id, role=role, content=content)

    async def get_messages_by_session(self, session_id: int) -> list[ChatMessage]:
        return await self._model.filter(session_id=session_id).order_by("created_at")
