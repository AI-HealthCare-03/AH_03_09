from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.dependencies.security import get_request_user
from app.dtos.chat import (
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatMessageSendRequest,
    ChatSendMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    MessageFeedbackRequest,
)
from app.models.users import User
from app.services.chat import ChatService

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: ChatSessionCreateRequest,
    current_user: Annotated[User, Depends(get_request_user)],
    chat_svc: Annotated[ChatService, Depends(ChatService)],
) -> ChatSessionResponse:
    session = await chat_svc.create_session(user_id=current_user.id, title=body.title)
    return ChatSessionResponse.model_validate(session)


@chat_router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    current_user: Annotated[User, Depends(get_request_user)],
    chat_svc: Annotated[ChatService, Depends(ChatService)],
) -> list[ChatSessionResponse]:
    sessions = await chat_svc.get_user_sessions(user_id=current_user.id)
    return [ChatSessionResponse.model_validate(s) for s in sessions]


@chat_router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session_detail(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_request_user)],
    chat_svc: Annotated[ChatService, Depends(ChatService)],
) -> ChatSessionDetailResponse:
    result = await chat_svc.get_session_detail(session_id=session_id, user_id=current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
    session, messages = result
    return ChatSessionDetailResponse(
        id=session.id,
        title=session.title,
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@chat_router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_request_user)],
    chat_svc: Annotated[ChatService, Depends(ChatService)],
) -> None:
    await chat_svc.delete_session(session_id=session_id, user_id=current_user.id)


@chat_router.get("/sessions/{session_id}/messages", response_model=ChatMessageListResponse)
async def list_messages(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_request_user)],
    chat_svc: Annotated[ChatService, Depends(ChatService)],
) -> ChatMessageListResponse:
    messages = await chat_svc.get_session_messages(session_id=session_id, user_id=current_user.id)
    if messages is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
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
    chat_svc: Annotated[ChatService, Depends(ChatService)],
) -> ChatSendMessageResponse:
    user_msg, assistant_msg = await chat_svc.send_message_sync(
        session_id=session_id, user_id=current_user.id, content=body.content
    )
    return ChatSendMessageResponse(
        user_message=ChatMessageResponse.model_validate(user_msg),
        assistant_message=ChatMessageResponse.model_validate(assistant_msg),
    )


@chat_router.post(
    "/sessions/{session_id}/messages/stream",
    summary="메시지 전송 (SSE 스트리밍)",
    description="AI 응답을 SSE(Server-Sent Events)로 실시간 스트리밍합니다.",
)
async def stream_message(
    session_id: UUID,
    body: ChatMessageSendRequest,
    current_user: Annotated[User, Depends(get_request_user)],
    chat_svc: Annotated[ChatService, Depends(ChatService)],
) -> StreamingResponse:
    return StreamingResponse(
        chat_svc.stream_message(session_id=session_id, user_id=current_user.id, content=body.content),
        media_type="text/event-stream",
    )


@chat_router.patch(
    "/sessions/{session_id}/messages/{message_id}/feedback",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
)
async def update_message_feedback(
    session_id: UUID,
    message_id: int,
    body: MessageFeedbackRequest,
    current_user: Annotated[User, Depends(get_request_user)],
    chat_svc: Annotated[ChatService, Depends(ChatService)],
) -> ChatMessageResponse:
    msg = await chat_svc.update_message_feedback(
        session_id=session_id,
        message_id=message_id,
        user_id=current_user.id,
        feedback=body.feedback,
    )
    return ChatMessageResponse.model_validate(msg)
