from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.chats import (
    ChatMessageResponse,
    ChatMessageSendRequest,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionResponse,
)
from app.models.users import User
from app.services.chats import ChatService

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: ChatSessionCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
) -> Response:
    result = await chat_service.create_session(user=user, data=body)
    return Response(result.model_dump(), status_code=status.HTTP_201_CREATED)


@chat_router.get("/sessions", response_model=list[ChatSessionResponse], status_code=status.HTTP_200_OK)
async def get_sessions(
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
) -> Response:
    result = await chat_service.get_sessions(user=user)
    return Response([r.model_dump() for r in result], status_code=status.HTTP_200_OK)


@chat_router.get(
    "/sessions/{session_id}", response_model=ChatSessionDetailResponse, status_code=status.HTTP_200_OK
)
async def get_session_detail(
    session_id: int,
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
) -> Response:
    result = await chat_service.get_session_detail(user=user, session_id=session_id)
    return Response(result.model_dump(), status_code=status.HTTP_200_OK)


@chat_router.post(
    "/sessions/{session_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK
)
async def send_message(
    session_id: int,
    body: ChatMessageSendRequest,
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
) -> Response:
    result = await chat_service.send_message(user=user, session_id=session_id, data=body)
    return Response(result.model_dump(), status_code=status.HTTP_200_OK)


@chat_router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
) -> None:
    await chat_service.delete_session(user=user, session_id=session_id)
