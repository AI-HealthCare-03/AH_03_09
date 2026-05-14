from typing import Annotated

from fastapi import APIRouter, Body, Depends, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.models.users import User
from app.services.chat import ChatService

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
    title: str = Body(default="새 대화", embed=True),
) -> Response:
    conv = chat_service.create_conversation(user_id=user.id, title=title)
    return Response(conv, status_code=status.HTTP_201_CREATED)


@chat_router.get("/conversations", status_code=status.HTTP_200_OK)
async def get_conversations(
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
) -> Response:
    convs = chat_service.get_conversations(user_id=user.id)
    return Response(convs, status_code=status.HTTP_200_OK)


@chat_router.get("/conversations/{conversation_id}", status_code=status.HTTP_200_OK)
async def get_conversation(
    conversation_id: str,
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
) -> Response:
    conv = chat_service.get_conversation_with_messages(conversation_id=conversation_id, user_id=user.id)
    return Response(conv, status_code=status.HTTP_200_OK)


@chat_router.post("/conversations/{conversation_id}/messages", status_code=status.HTTP_200_OK)
async def send_message(
    conversation_id: str,
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
    content: str = Body(..., embed=True),
) -> Response:
    msg = chat_service.send_message(conversation_id=conversation_id, user_id=user.id, content=content)
    return Response(msg, status_code=status.HTTP_200_OK)


@chat_router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
) -> None:
    chat_service.delete_conversation(conversation_id=conversation_id, user_id=user.id)
