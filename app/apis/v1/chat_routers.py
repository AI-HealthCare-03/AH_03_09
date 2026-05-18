from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status

from app.dependencies.security import get_request_user
from app.dtos.chat import (
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatMessageSendRequest,
    ChatSendMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionResponse,
)
from app.models.users import User
from app.repositories.chat_repository import ChatRepository
from app.services.chat import ChatService
from app.services.jwt import JwtService

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: ChatSessionCreateRequest,
    current_user: Annotated[User, Depends(get_request_user)],
) -> ChatSessionResponse:
    session = await ChatService().create_session(user_id=current_user.id, title=body.title)
    return ChatSessionResponse.model_validate(session)


@chat_router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    current_user: Annotated[User, Depends(get_request_user)],
) -> list[ChatSessionResponse]:
    sessions = await ChatService().get_user_sessions(user_id=current_user.id)
    return [ChatSessionResponse.model_validate(s) for s in sessions]


@chat_router.get("/sessions/{session_id}/messages", response_model=ChatMessageListResponse)
async def list_messages(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_request_user)],
) -> ChatMessageListResponse:
    messages = await ChatService().get_session_messages(session_id=session_id, user_id=current_user.id)
    return ChatMessageListResponse(messages=[ChatMessageResponse.model_validate(m) for m in messages])


@chat_router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatSendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="메시지 전송 (Swagger 테스트용 동기 REST)",
    description="WebSocket과 동일한 흐름이지만 모든 스트림 응답을 모아 한 번에 반환합니다. "
    "실시간 스트리밍이 필요하면 WebSocket(/chat/ws/{session_id})을 사용하세요.",
)
async def send_message(
    session_id: UUID,
    body: ChatMessageSendRequest,
    current_user: Annotated[User, Depends(get_request_user)],
) -> ChatSendMessageResponse:
    user_msg, assistant_msg = await ChatService().send_message_sync(
        session_id=session_id, user_id=current_user.id, content=body.content
    )
    return ChatSendMessageResponse(
        user_message=ChatMessageResponse.model_validate(user_msg),
        assistant_message=ChatMessageResponse.model_validate(assistant_msg),
    )


@chat_router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    token: str,
) -> None:
    # JWT 검증 (WebSocket은 헤더 인증 대신 query param 사용)
    try:
        verified = JwtService().verify_jwt(token=token, token_type="access")
        user_id: int = verified.payload["user_id"]
    except HTTPException:
        await websocket.close(code=1008)
        return

    # 세션 소유권 확인
    session = await ChatRepository().get_session(session_id, user_id)
    if not session:
        await websocket.close(code=1008)
        return

    await ChatService().handle_websocket(websocket, session_id, user_id)
