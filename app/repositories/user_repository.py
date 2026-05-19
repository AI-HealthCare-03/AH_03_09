from datetime import UTC, datetime

from app.models.users import User


class UserRepository:
    async def get_user(self, user_id: int) -> User | None:
        return await User.filter(id=user_id, is_active=True).first()

    async def get_by_kakao_id(self, kakao_id: str) -> User | None:
        return await User.filter(kakao_id=kakao_id, is_active=True).first()

    async def upsert_kakao_user(
        self,
        kakao_id: str,
        email: str | None,
        name: str | None,
        gender: str | None,
        age_range: str | None,
        birthday: str | None,
        birthyear: str | None,
        phone_number: str | None,
    ) -> User:
        user, _ = await User.update_or_create(
            kakao_id=kakao_id,
            defaults={
                "email": email,
                "name": name,
                "gender": gender,
                "age_range": age_range,
                "birthday": birthday,
                "birthyear": birthyear,
                "phone_number": phone_number,
                "is_active": True,
                "deleted_at": None,
            },
        )
        return user

    async def soft_delete(self, user_id: int) -> None:
        await User.filter(id=user_id).update(
            is_active=False,
            deleted_at=datetime.now(UTC),
        )
