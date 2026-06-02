import asyncio
import json
import time
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.sqlalchemy_client import get_async_session
from app.core.redis_client import get_redis
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.health_profiles import HealthProfile
from app.repositories.chat_repository import ChatRepository
from app.services.guides import GuideService

RESPONSE_TIMEOUT_SECONDS = 60
DELAY_WARNING_SECONDS = 10

_DANGER_KEYWORDS = [
    "자살",
    "자해",
    "죽고 싶",
    "죽고싶",
    "죽을 것 같",
    "극단적 선택",
    "과다복용",
    "약 다 먹",
    "전부 먹으면",
    "목을 매",
    "뛰어내려",
]
_INAPPROPRIATE_KEYWORDS = ["씨발", "개새끼", "병신", "ㅅㅂ", "ㅂㅅ", "좆"]

_DANGER_RESPONSE = (
    "지금 많이 힘드신 것 같아요. 혼자 감당하기 어려운 순간이라면 전문가의 도움을 받으시길 권합니다.\n\n"
    "📞 자살예방상담전화 1393 (24시간)\n"
    "📞 정신건강위기상담전화 1577-0199 (24시간)\n\n"
    "약물과 관련된 응급 상황이라면 즉시 119에 연락하거나 가까운 응급실을 방문해 주세요.\n\n"
    "⚠️ 본 답변은 AI가 생성한 의료 정보입니다. 정확한 복약 지도는 담당 의사·약사에게 확인하시기 바랍니다."
)
_INAPPROPRIATE_RESPONSE = "죄송합니다. 해당 질문에는 답변하기 어렵습니다. 약물 복용 및 건강 관련 질문을 부탁드립니다."


def _check_content(content: str) -> str:
    """위험/부적절 키워드 여부를 반환한다. 정상이면 'ok'."""
    if any(kw in content for kw in _DANGER_KEYWORDS):
        return "danger"
    if any(kw in content for kw in _INAPPROPRIATE_KEYWORDS):
        return "inappropriate"
    return "ok"


_PRESET_RESPONSES = {
    "danger": _DANGER_RESPONSE,
    "inappropriate": _INAPPROPRIATE_RESPONSE,
}


class ChatService:
    def __init__(self, session: Annotated[AsyncSession, Depends(get_async_session)]) -> None:
        self.session = session
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

    async def _fetch_health_context(self, user_id: int) -> dict | None:
        result = await self.session.execute(select(HealthProfile).where(HealthProfile.user_id == user_id))
        health_profile = result.scalar_one_or_none()
        if not health_profile:
            return None
        return {
            "primary_conditions": health_profile.primary_conditions,
            "allergies": health_profile.allergies,
            "current_medications": health_profile.current_medications,
            "lifestyle_exercise": health_profile.lifestyle_exercise,
            "lifestyle_smoking": health_profile.lifestyle_smoking,
            "lifestyle_alcohol": health_profile.lifestyle_alcohol,
        }

    async def _get_guide_context(self, guide_id: str | None) -> dict | None:
        if not guide_id:
            return None
        try:
            ctx = await GuideService().get_guide_context(guide_id)
            return {
                "medications": ctx.medications,
                "schedule": ctx.schedule,
                "key_instructions": ctx.key_instructions,
            }
        except HTTPException:
            return None

    async def stream_message(self, session_id: UUID | str, user_id: int, content: str, guide_id: str | None = None):
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            yield json.dumps({"type": "error", "detail": "세션을 찾을 수 없습니다."}) + "\n"
            return

        preset = _PRESET_RESPONSES.get(_check_content(content))
        if preset:
            await self.repo.create_message(session_id, MessageRole.USER, content)
            await self.repo.create_message(session_id, MessageRole.ASSISTANT, preset)
            yield json.dumps({"type": "chunk", "chunk": preset}) + "\n"
            yield json.dumps({"type": "done", "content": preset}) + "\n"
            return

        await self.repo.create_message(session_id, MessageRole.USER, content)

        history = await self.repo.get_messages(session_id, limit=20)
        history_payload = [{"role": m.role, "content": m.content} for m in history[:-1]]

        health_context = await self._fetch_health_context(user_id)
        guide_context = await self._get_guide_context(guide_id)

        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"chat:stream:{session_id}")

        task_payload = json.dumps(
            {
                "session_id": str(session_id),
                "user_message": content,
                "history": history_payload,
                "health_profile": health_context,
                "guide_context": guide_context,
            }
        )
        await redis.publish(f"chat:request:{session_id}", task_payload)

        full_response: list[str] = []
        start_time = time.monotonic()
        delay_sent = False
        try:
            async with asyncio.timeout(RESPONSE_TIMEOUT_SECONDS):
                async for redis_msg in pubsub.listen():
                    if not delay_sent and not full_response and (time.monotonic() - start_time) > DELAY_WARNING_SECONDS:
                        yield (
                            json.dumps({"type": "delay", "detail": "AI 응답이 지연되고 있습니다. 잠시만 기다려주세요."})
                            + "\n"
                        )
                        delay_sent = True
                    if redis_msg["type"] != "message":
                        continue
                    data: str = redis_msg["data"]
                    if data.startswith("[ERROR]"):
                        yield json.dumps({"type": "error", "detail": data[7:]}) + "\n"
                        return
                    if data == "[DONE]":
                        break
                    full_response.append(data)
                    yield json.dumps({"type": "chunk", "chunk": data}) + "\n"
        except TimeoutError:
            yield json.dumps({"type": "error", "detail": "AI 응답 시간 초과. 다시 시도해 주세요."}) + "\n"
            return
        finally:
            await pubsub.unsubscribe(f"chat:stream:{session_id}")
            await pubsub.aclose()

        complete = "".join(full_response)
        if complete:
            await self.repo.create_message(session_id, MessageRole.ASSISTANT, complete)
            await self.repo.touch_session(session_id)

        yield json.dumps({"type": "done", "content": complete}) + "\n"

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
        self, session_id: UUID | str, user_id: int, content: str, guide_id: str | None = None
    ) -> tuple[ChatMessage, ChatMessage]:
        """Swagger 테스트용 REST 래퍼: WebSocket과 동일한 흐름이지만 모든 스트림을 모아 한 번에 반환."""
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")

        preset = _PRESET_RESPONSES.get(_check_content(content))
        if preset:
            user_msg = await self.repo.create_message(session_id, MessageRole.USER, content)
            assistant_msg = await self.repo.create_message(session_id, MessageRole.ASSISTANT, preset)
            return user_msg, assistant_msg

        user_msg = await self.repo.create_message(session_id, MessageRole.USER, content)

        history = await self.repo.get_messages(session_id, limit=20)
        history_payload = [{"role": m.role, "content": m.content} for m in history[:-1]]

        health_context = await self._fetch_health_context(user_id)
        guide_context = await self._get_guide_context(guide_id)

        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"chat:stream:{session_id}")

        task_payload = json.dumps(
            {
                "session_id": str(session_id),
                "user_message": content,
                "history": history_payload,
                "health_profile": health_context,
                "guide_context": guide_context,
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
        if not complete:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI 응답 실패: 빈 응답")
        assistant_msg = await self.repo.create_message(session_id, MessageRole.ASSISTANT, complete)
        await self.repo.touch_session(session_id)
        return user_msg, assistant_msg
