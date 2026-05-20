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
from app.repositories.health_profile_repository import HealthProfileRepository

AI_TASK_QUEUE = "ai:chat:queue"
AI_RESULT_PREFIX = "ai:chat:result:"
AI_RESULT_TTL = 300
AI_POLL_TIMEOUT = 30
AI_STREAM_PREFIX = "ai:chat:stream:"
AI_STREAM_CHUNK_TIMEOUT = 30


class ChatService:
    def __init__(self):
        self.session_repo = ChatSessionRepository()
        self.message_repo = ChatMessageRepository()
        self.health_profile_repo = HealthProfileRepository()

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
        health_profile = await self.health_profile_repo.get_by_user_id(user.id)

        ai_result = await self._request_ai_response(
            session_id=session.id,
            user_message=data.content,
            history=history,
            health_profile=health_profile,
        )

        async with in_transaction():
            if ai_result.get("title") and not history:
                await self.session_repo.update_title(session, ai_result["title"])
            await self.message_repo.create(
                session_id=session.id,
                role=MessageRole.USER,
                content=data.content,
            )
            ai_message = await self.message_repo.create(
                session_id=session.id,
                role=MessageRole.ASSISTANT,
                content=ai_result["answer"],
            )

        return ChatMessageResponse.model_validate(ai_message)

    async def stream_message(self, user: User, session_id: int, data: ChatMessageSendRequest):
        try:
            session = await self._get_owned_session(user, session_id)
        except HTTPException as e:
            yield f"event: error\ndata: {json.dumps({'detail': e.detail})}\n\n"
            return

        history = await self.message_repo.get_messages_by_session(session_id=session.id)
        health_profile = await self.health_profile_repo.get_by_user_id(user.id)

        task_id = uuid.uuid4().hex
        payload = json.dumps(
            {
                "task_id": task_id,
                "session_id": session.id,
                "user_message": data.content,
                "stream": True,
                "history": [{"role": m.role, "content": m.content} for m in history],
                "health_profile": {
                    "primary_conditions": health_profile.primary_conditions,
                    "allergies": health_profile.allergies,
                    "current_medications": health_profile.current_medications,
                    "lifestyle_exercise": health_profile.lifestyle_exercise,
                    "lifestyle_smoking": health_profile.lifestyle_smoking,
                    "lifestyle_alcohol": health_profile.lifestyle_alcohol,
                }
                if health_profile
                else None,
            }
        )

        redis = await get_redis()
        await redis.lpush(AI_TASK_QUEUE, payload)

        stream_key = f"{AI_STREAM_PREFIX}{task_id}"
        full_text = ""

        while True:
            raw = await redis.blpop(stream_key, timeout=AI_STREAM_CHUNK_TIMEOUT)
            if raw is None:
                yield f"event: error\ndata: {json.dumps({'detail': 'AI 스트리밍 응답 시간이 초과되었습니다.'})}\n\n"
                return

            chunk_data = json.loads(raw[1])

            if chunk_data.get("error"):
                yield f"event: error\ndata: {json.dumps({'detail': chunk_data['error']})}\n\n"
                return

            if chunk_data["done"]:
                full_text = chunk_data.get("full_text", full_text)
                title = chunk_data.get("title")
                break

            full_text += chunk_data["chunk"]
            yield f"data: {json.dumps({'chunk': chunk_data['chunk']})}\n\n"

        async with in_transaction():
            if title and not history:
                await self.session_repo.update_title(session, title)
            await self.message_repo.create(session_id=session.id, role=MessageRole.USER, content=data.content)
            ai_message = await self.message_repo.create(
                session_id=session.id, role=MessageRole.ASSISTANT, content=full_text
            )

        yield f"event: done\ndata: {json.dumps({'message_id': ai_message.id, 'title': title})}\n\n"

    async def delete_session(self, user: User, session_id: int) -> None:
        session = await self._get_owned_session(user, session_id)
        await self.session_repo.delete(session)

    async def _get_owned_session(self, user: User, session_id: int):
        session = await self.session_repo.get_by_id_and_user(session_id=session_id, user_id=user.id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채팅 세션을 찾을 수 없습니다.")
        return session

    async def _request_ai_response(
        self, session_id: int, user_message: str, history: list, health_profile=None
    ) -> dict:
        task_id = uuid.uuid4().hex
        payload = json.dumps(
            {
                "task_id": task_id,
                "session_id": session_id,
                "user_message": user_message,
                "history": [{"role": m.role, "content": m.content} for m in history],
                "health_profile": {
                    "primary_conditions": health_profile.primary_conditions,
                    "allergies": health_profile.allergies,
                    "current_medications": health_profile.current_medications,
                    "lifestyle_exercise": health_profile.lifestyle_exercise,
                    "lifestyle_smoking": health_profile.lifestyle_smoking,
                    "lifestyle_alcohol": health_profile.lifestyle_alcohol,
                }
                if health_profile
                else None,
            }
        )

        redis = await get_redis()
        await redis.lpush(AI_TASK_QUEUE, payload)

        result_key = f"{AI_RESULT_PREFIX}{task_id}"
        result = await redis.blpop(result_key, timeout=AI_POLL_TIMEOUT)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI 응답 시간이 초과되었습니다. 다시 시도해 주세요.",
            )

        return json.loads(result[1])
