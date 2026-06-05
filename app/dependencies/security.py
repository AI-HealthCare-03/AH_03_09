from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.sqlalchemy_client import get_async_session
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService


async def get_request_user(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    if not access_token:
        raise HTTPException(detail="인증에 실패했습니다.", status_code=status.HTTP_401_UNAUTHORIZED)
    verified = JwtService().verify_jwt(token=access_token, token_type="access")
    user_id = verified.payload["user_id"]
    user = await UserRepository(session).get_user(user_id)
    if not user:
        raise HTTPException(detail="인증에 실패했습니다.", status_code=status.HTTP_401_UNAUTHORIZED)
    return user
