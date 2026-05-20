from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id, User.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_kakao_id(self, kakao_id: str) -> User | None:
        stmt = select(User).where(User.kakao_id == kakao_id, User.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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
        values = {
            "kakao_id": kakao_id,
            "email": email,
            "name": name,
            "gender": gender,
            "age_range": age_range,
            "birthday": birthday,
            "birthyear": birthyear,
            "phone_number": phone_number,
            "is_active": True,
            "deleted_at": None,
        }

        stmt = (
            pg_insert(User)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[User.kakao_id],
                set_={k: v for k, v in values.items() if k != "kakao_id"},
            )
            .returning(User)
        )

        result = await self.session.execute(stmt)
        await self.session.commit()
        user = result.scalar_one()
        await self.session.refresh(user)
        return user

    async def soft_delete(self, user_id: int) -> None:
        stmt = update(User).where(User.id == user_id).values(is_active=False, deleted_at=datetime.now(UTC))
        await self.session.execute(stmt)
        await self.session.commit()
