from app.models.users import User
from app.repositories.user_repository import UserRepository


class UserManageService:
    def __init__(self) -> None:
        self.repo = UserRepository()

    def get_user(self, user_id: str) -> User | None:
        return self.repo.get_user(user_id)

    async def withdraw(self, user_id: int) -> None:
        await self.repo.soft_delete(user_id)
