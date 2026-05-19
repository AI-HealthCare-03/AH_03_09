import json
import uuid

from fastapi import HTTPException
from starlette import status
from tortoise.transactions import in_transaction

from app.core.redis_client import get_redis
from app.dtos.chats import (
    ChatMessageResponse,
    ChatMessageSendRequest,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionResponse,
)
from app.models.chats import MessageRole
from app.models.users import User
from app.repositories.chat_repository import ChatMessageRepository, ChatSessionRepository

AI_TASK_QUEUE = "ai:chat:queue"
AI_RESULT_PREFIX = "ai:chat:result:"
AI_RESULT_TTL = 300
AI_POLL_TIMEOUT = 30


class ChatService:
    def __init__(self):
        self.session_repo = ChatSessionRepository()
        self.message_repo = ChatMessageRepository()

    async def create_session(self, user: User, data: ChatSessionCreateRequest) -> ChatSessionResponse:
        session = await self.session_repo.create(user_id=user.id, title=data.title)
        return ChatSessionResponse.model_validate(session)

    async def get_sessions(self, user: User) -> list[ChatSessionResponse]:
        sessions = await self.session_repo.get_all_by_user(user_id=user.id)
        return [ChatSessionResponse.model_validate(s) for s in sessions]

    async def get_session_detail(self, user: User, session_id: int) -> ChatSessionDetailResponse:
        session = await self._get_owned_session(user, session_id)
        messages = await self.message_repo.get_messages_by_session(session_id=session.id)
        return ChatSessionDetailResponse(
            id=session.id,
            title=session.title,
            messages=[ChatMessageResponse.model_validate(m) for m in messages],
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    async def send_message(self, user: User, session_id: int, data: ChatMessageSendRequest) -> ChatMessageResponse:
        session = await self._get_owned_session(user, session_id)

        history = await self.message_repo.get_messages_by_session(session_id=session.id)

        ai_response_text = await self._request_ai_response(
            session_id=session.id,
            user_message=data.content,
            history=history,
        )

        async with in_transaction():
            await self.message_repo.create(
                session_id=session.id,
                role=MessageRole.USER,
                content=data.content,
            )
            ai_message = await self.message_repo.create(
                session_id=session.id,
                role=MessageRole.ASSISTANT,
                content=ai_response_text,
            )

        return ChatMessageResponse.model_validate(ai_message)

    async def delete_session(self, user: User, session_id: int) -> None:
        session = await self._get_owned_session(user, session_id)
        await self.session_repo.delete(session)

    async def _get_owned_session(self, user: User, session_id: int):
        session = await self.session_repo.get_by_id_and_user(session_id=session_id, user_id=user.id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채팅 세션을 찾을 수 없습니다.")
        return session

    async def _request_ai_response(self, session_id: int, user_message: str, history: list) -> str:
        task_id = uuid.uuid4().hex
        payload = json.dumps({
            "task_id": task_id,
            "session_id": session_id,
            "user_message": user_message,
            "history": [{"role": m.role, "content": m.content} for m in history],
        })

        redis = await get_redis()
        await redis.lpush(AI_TASK_QUEUE, payload)

        result_key = f"{AI_RESULT_PREFIX}{task_id}"
        result = await redis.blpop(result_key, timeout=AI_POLL_TIMEOUT)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI 응답 시간이 초과되었습니다. 다시 시도해 주세요.",
            )

        response_data = json.loads(result[1])
        return response_data["answer"]
