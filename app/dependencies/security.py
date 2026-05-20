from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.sqlalchemy_client import get_async_session
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService

security = HTTPBearer()


async def get_request_user(
    credential: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    token = credential.credentials
    verified = JwtService().verify_jwt(token=token, token_type="access")
    user_id = verified.payload["user_id"]
    user = await UserRepository(session).get_user(user_id)
    if not user:
        raise HTTPException(detail="인증에 실패했습니다.", status_code=status.HTTP_401_UNAUTHORIZED)
    return user
