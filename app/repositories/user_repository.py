from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_kakao_id(self, kakao_id: str) -> User | None:
        stmt = select(User).where(User.kakao_id == kakao_id)
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

    async def hard_delete(self, user_id: int) -> None:
        # ocr_corrections.corrected_by 는 CASCADE 가 없으므로 먼저 비운다.
        # chat_sessions / ocr_documents 와 그 하위 테이블은 FK CASCADE 로 함께 삭제됨.
        await self.session.execute(
            text("DELETE FROM ocr_corrections WHERE corrected_by = :uid"),
            {"uid": user_id},
        )
        await self.session.execute(delete(User).where(User.id == user_id))
        await self.session.commit()
