import asyncio
import json
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.sqlalchemy_client import get_async_session
from app.core.redis_client import get_redis
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.health_profiles import HealthProfile
from app.repositories.chat_repository import ChatRepository

RESPONSE_TIMEOUT_SECONDS = 60


class ChatService:
    def __init__(self, session: Annotated[AsyncSession, Depends(get_async_session)]) -> None:
        self.repo = ChatRepository(session)

    async def update_message_feedback(
        self, session_id: UUID | str, message_id: int, user_id: int, feedback: str
    ) -> ChatMessage:
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
        msg = await self.repo.update_message_feedback(message_id, session_id, feedback)
        if not msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="메시지를 찾을 수 없습니다.")
        return msg

    async def get_session_detail(self, session_id: UUID | str, user_id: int) -> tuple[ChatSession, list] | None:
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            return None
        messages = await self.repo.get_messages(session_id)
        return session, messages

    async def delete_session(self, session_id: UUID | str, user_id: int) -> None:
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
        await self.repo.delete_session(session_id)

    async def stream_message(self, session_id: UUID | str, user_id: int, content: str):
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            yield f"event: error\ndata: {json.dumps({'detail': '세션을 찾을 수 없습니다.'})}\n\n"
            return

        await self.repo.create_message(session_id, MessageRole.USER, content)

        history = await self.repo.get_messages(session_id, limit=20)
        history_payload = [{"role": m.role, "content": m.content} for m in history[:-1]]

        health_profile = await HealthProfile.get_or_none(user_id=user_id)
        health_context = (
            {
                "primary_conditions": health_profile.primary_conditions,
                "allergies": health_profile.allergies,
                "current_medications": health_profile.current_medications,
                "lifestyle_exercise": health_profile.lifestyle_exercise,
                "lifestyle_smoking": health_profile.lifestyle_smoking,
                "lifestyle_alcohol": health_profile.lifestyle_alcohol,
            }
            if health_profile
            else None
        )

        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"chat:stream:{session_id}")

        task_payload = json.dumps(
            {
                "session_id": str(session_id),
                "user_message": content,
                "history": history_payload,
                "health_profile": health_context,
            }
        )
        await redis.publish(f"chat:request:{session_id}", task_payload)

        full_response: list[str] = []
        try:
            async with asyncio.timeout(RESPONSE_TIMEOUT_SECONDS):
                async for redis_msg in pubsub.listen():
                    if redis_msg["type"] != "message":
                        continue
                    data: str = redis_msg["data"]
                    if data.startswith("[ERROR]"):
                        yield f"event: error\ndata: {json.dumps({'detail': data[7:]})}\n\n"
                        return
                    if data == "[DONE]":
                        break
                    full_response.append(data)
                    yield f"data: {json.dumps({'chunk': data})}\n\n"
        except TimeoutError:
            yield f"event: error\ndata: {json.dumps({'detail': 'AI 응답 시간 초과'})}\n\n"
            return
        finally:
            await pubsub.unsubscribe(f"chat:stream:{session_id}")
            await pubsub.aclose()

        complete = "".join(full_response)
        if complete:
            await self.repo.create_message(session_id, MessageRole.ASSISTANT, complete)
            await self.repo.touch_session(session_id)

        yield f"event: done\ndata: {json.dumps({'content': complete})}\n\n"

    async def create_session(self, user_id: int, title: str = "새 대화") -> ChatSession:
        return await self.repo.create_session(user_id, title)

    async def get_user_sessions(self, user_id: int) -> list[ChatSession]:
        return await self.repo.get_sessions(user_id)

    async def get_session_messages(self, session_id: UUID | str, user_id: int) -> list | None:
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            return None
        return await self.repo.get_messages(session_id)

    async def send_message_sync(
        self, session_id: UUID | str, user_id: int, content: str
    ) -> tuple[ChatMessage, ChatMessage]:
        """Swagger 테스트용 REST 래퍼: WebSocket과 동일한 흐름이지만 모든 스트림을 모아 한 번에 반환."""
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")

        user_msg = await self.repo.create_message(session_id, MessageRole.USER, content)

        history = await self.repo.get_messages(session_id, limit=20)
        history_payload = [{"role": m.role, "content": m.content} for m in history[:-1]]

        health_profile = await HealthProfile.get_or_none(user_id=user_id)
        health_context = (
            {
                "primary_conditions": health_profile.primary_conditions,
                "allergies": health_profile.allergies,
                "current_medications": health_profile.current_medications,
                "lifestyle_exercise": health_profile.lifestyle_exercise,
                "lifestyle_smoking": health_profile.lifestyle_smoking,
                "lifestyle_alcohol": health_profile.lifestyle_alcohol,
            }
            if health_profile
            else None
        )

        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"chat:stream:{session_id}")

        task_payload = json.dumps(
            {
                "session_id": str(session_id),
                "user_message": content,
                "history": history_payload,
                "health_profile": health_context,
            }
        )
        await redis.publish(f"chat:request:{session_id}", task_payload)

        full_response: list[str] = []
        error_detail: str | None = None
        try:
            async with asyncio.timeout(RESPONSE_TIMEOUT_SECONDS):
                async for redis_msg in pubsub.listen():
                    if redis_msg["type"] != "message":
                        continue
                    data: str = redis_msg["data"]
                    if data.startswith("[ERROR]"):
                        error_detail = data[7:]
                        break
                    if data == "[DONE]":
                        break
                    full_response.append(data)
        except TimeoutError:
            error_detail = "AI 응답 시간 초과"
        finally:
            await pubsub.unsubscribe(f"chat:stream:{session_id}")
            await pubsub.aclose()

        if error_detail:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI 응답 실패: {error_detail}")

        complete = "".join(full_response)
        assistant_msg = await self.repo.create_message(session_id, MessageRole.ASSISTANT, complete)
        await self.repo.touch_session(session_id)
        return user_msg, assistant_msg
