import asyncio
import json
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.sqlalchemy_client import get_async_session
from app.core.redis_client import get_redis
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.repositories.chat_repository import ChatRepository

RESPONSE_TIMEOUT_SECONDS = 60


class ChatService:
    def __init__(self, session: Annotated[AsyncSession, Depends(get_async_session)]) -> None:
        self.repo = ChatRepository(session)

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

        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"chat:stream:{session_id}")

        task_payload = json.dumps(
            {
                "session_id": str(session_id),
                "user_message": content,
                "history": history_payload,
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

    async def handle_websocket(self, websocket: WebSocket, session_id: str, user_id: int) -> None:
        await websocket.accept()
        redis = await get_redis()

        try:
            while True:
                user_text = await websocket.receive_text()
                if not user_text.strip():
                    continue

                # 유저 메시지 저장
                await self.repo.create_message(session_id, MessageRole.USER, user_text)

                # 히스토리 조회 (최근 20개)
                history = await self.repo.get_messages(session_id, limit=20)
                history_payload = [{"role": msg.role, "content": msg.content} for msg in history[:-1]]

                # AI Worker에 task 발행
                task_payload = json.dumps(
                    {
                        "session_id": session_id,
                        "user_message": user_text,
                        "history": history_payload,
                    }
                )
                await redis.publish(f"chat:request:{session_id}", task_payload)

                # 스트리밍 응답 수신
                pubsub = redis.pubsub()
                await pubsub.subscribe(f"chat:stream:{session_id}")

                full_response: list[str] = []
                async for redis_msg in pubsub.listen():
                    if redis_msg["type"] != "message":
                        continue
                    data: str = redis_msg["data"]
                    if data.startswith("[ERROR]"):
                        await websocket.send_text(json.dumps({"type": "error", "content": data[7:]}))
                        break
                    if data == "[DONE]":
                        break
                    full_response.append(data)
                    await websocket.send_text(json.dumps({"type": "stream", "content": data}))

                await pubsub.unsubscribe(f"chat:stream:{session_id}")
                await pubsub.aclose()

                # 완성된 응답 저장
                complete_text = "".join(full_response)
                if complete_text:
                    await self.repo.create_message(session_id, MessageRole.ASSISTANT, complete_text)
                    await self.repo.touch_session(session_id)

                await websocket.send_text(json.dumps({"type": "done", "content": complete_text}))

        except WebSocketDisconnect:
            pass
