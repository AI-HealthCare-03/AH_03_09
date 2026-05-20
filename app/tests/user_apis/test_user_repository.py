import pytest

from app.models.base import Base
from app.models.users import User
from app.repositories.user_repository import UserRepository


@pytest.fixture
def repo(db_session):
    return UserRepository(db_session)


class TestUserRepository:
    async def test_upsert_creates_new_user(self, repo):
        user = await repo.upsert_kakao_user(
            kakao_id="kakao-1",
            email="a@x.com",
            name="홍길동",
            gender="male",
            age_range="20~29",
            birthday="0101",
            birthyear="2000",
            phone_number="010-1234-5678",
        )
        assert user.id is not None
        assert user.kakao_id == "kakao-1"
        assert user.email == "a@x.com"
        assert user.is_active is True
        assert user.deleted_at is None

    async def test_upsert_updates_existing_user_on_same_kakao_id(self, repo):
        first = await repo.upsert_kakao_user(
            kakao_id="kakao-2",
            email="old@x.com",
            name="이전",
            gender=None,
            age_range=None,
            birthday=None,
            birthyear=None,
            phone_number=None,
        )
        second = await repo.upsert_kakao_user(
            kakao_id="kakao-2",
            email="new@x.com",
            name="새이름",
            gender="female",
            age_range="30~39",
            birthday="0202",
            birthyear="1990",
            phone_number="010-9999-9999",
        )
        assert first.id == second.id
        assert second.email == "new@x.com"
        assert second.name == "새이름"
        assert second.gender == "female"

    async def test_upsert_reactivates_soft_deleted_user(self, repo):
        user = await repo.upsert_kakao_user(
            kakao_id="kakao-3",
            email="a@x.com",
            name=None,
            gender=None,
            age_range=None,
            birthday=None,
            birthyear=None,
            phone_number=None,
        )
        await repo.soft_delete(user.id)
        assert await repo.get_user(user.id) is None

        revived = await repo.upsert_kakao_user(
            kakao_id="kakao-3",
            email="a@x.com",
            name=None,
            gender=None,
            age_range=None,
            birthday=None,
            birthyear=None,
            phone_number=None,
        )
        assert revived.id == user.id
        assert revived.is_active is True
        assert revived.deleted_at is None

    async def test_get_user_returns_active_user(self, repo):
        created = await repo.upsert_kakao_user(
            kakao_id="kakao-4",
            email=None,
            name=None,
            gender=None,
            age_range=None,
            birthday=None,
            birthyear=None,
            phone_number=None,
        )
        fetched = await repo.get_user(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_user_excludes_soft_deleted(self, repo):
        user = await repo.upsert_kakao_user(
            kakao_id="kakao-5",
            email=None,
            name=None,
            gender=None,
            age_range=None,
            birthday=None,
            birthyear=None,
            phone_number=None,
        )
        await repo.soft_delete(user.id)
        assert await repo.get_user(user.id) is None

    async def test_get_by_kakao_id(self, repo):
        await repo.upsert_kakao_user(
            kakao_id="kakao-6",
            email=None,
            name=None,
            gender=None,
            age_range=None,
            birthday=None,
            birthyear=None,
            phone_number=None,
        )
        found = await repo.get_by_kakao_id("kakao-6")
        assert found is not None
        assert found.kakao_id == "kakao-6"

        missing = await repo.get_by_kakao_id("nonexistent")
        assert missing is None

    async def test_soft_delete_sets_flags(self, repo, db_session):
        user = await repo.upsert_kakao_user(
            kakao_id="kakao-7",
            email=None,
            name=None,
            gender=None,
            age_range=None,
            birthday=None,
            birthyear=None,
            phone_number=None,
        )
        await repo.soft_delete(user.id)
        await db_session.refresh(user)
        assert user.is_active is False
        assert user.deleted_at is not None

    async def test_model_class_is_sqlalchemy(self):
        """User가 SQLAlchemy 모델이어야 함 (Tortoise 잔재 검증)."""
        assert issubclass(User, Base)
