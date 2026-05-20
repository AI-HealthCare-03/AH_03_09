from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.sqlalchemy_client import get_async_session
from app.models.users import User
from app.repositories.user_repository import UserRepository


class UserManageService:
    def __init__(self, session: Annotated[AsyncSession, Depends(get_async_session)]) -> None:
        self.repo = UserRepository(session)

    async def get_user(self, user_id: int) -> User | None:
        return await self.repo.get_user(user_id)

    async def withdraw(self, user_id: int) -> None:
        await self.repo.soft_delete(user_id)
