import asyncio

import pytest

from app.models.base import Base
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.repositories.chat_repository import ChatRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture
async def user_id(db_session) -> int:
    """FK 충족을 위한 User 1명 생성."""
    user = await UserRepository(db_session).upsert_kakao_user(
        kakao_id="chat-test-user",
        email=None,
        name=None,
        gender=None,
        age_range=None,
        birthday=None,
        birthyear=None,
        phone_number=None,
    )
    return user.id


@pytest.fixture
def repo(db_session):
    return ChatRepository(db_session)


class TestChatRepository:
    async def test_create_session(self, repo, user_id):
        s = await repo.create_session(user_id=user_id, title="첫 대화")
        assert s.id is not None
        assert s.user_id == user_id
        assert s.title == "첫 대화"
        assert s.created_at is not None
        assert s.updated_at is not None

    async def test_create_session_default_title(self, repo, user_id):
        s = await repo.create_session(user_id=user_id)
        assert s.title == "새 대화"

    async def test_get_sessions_ordered_by_updated_at_desc(self, repo, user_id):
        s1 = await repo.create_session(user_id=user_id, title="첫번째")
        await asyncio.sleep(0.01)
        s2 = await repo.create_session(user_id=user_id, title="두번째")

        sessions = await repo.get_sessions(user_id)
        assert len(sessions) == 2
        assert sessions[0].id == s2.id  # 최신이 먼저
        assert sessions[1].id == s1.id

    async def test_get_sessions_filters_by_user(self, repo, user_id, db_session):
        await repo.create_session(user_id=user_id, title="my")

        other_user = await UserRepository(db_session).upsert_kakao_user(
            kakao_id="other-user",
            email=None,
            name=None,
            gender=None,
            age_range=None,
            birthday=None,
            birthyear=None,
            phone_number=None,
        )
        await repo.create_session(user_id=other_user.id, title="other")

        sessions = await repo.get_sessions(user_id)
        assert len(sessions) == 1
        assert sessions[0].title == "my"

    async def test_get_session_returns_owner_only(self, repo, user_id):
        s = await repo.create_session(user_id=user_id, title="x")
        found = await repo.get_session(s.id, user_id)
        assert found is not None
        assert found.id == s.id

        # 다른 user_id로 조회하면 None
        not_found = await repo.get_session(s.id, user_id + 9999)
        assert not_found is None

    async def test_create_and_get_messages(self, repo, user_id):
        s = await repo.create_session(user_id=user_id)
        u = await repo.create_message(s.id, MessageRole.USER, "안녕")
        a = await repo.create_message(s.id, MessageRole.ASSISTANT, "안녕하세요")

        msgs = await repo.get_messages(s.id)
        assert len(msgs) == 2
        assert msgs[0].id == u.id
        assert msgs[0].role == MessageRole.USER.value
        assert msgs[0].content == "안녕"
        assert msgs[1].id == a.id
        assert msgs[1].role == MessageRole.ASSISTANT.value

    async def test_get_messages_respects_limit(self, repo, user_id):
        s = await repo.create_session(user_id=user_id)
        for i in range(5):
            await repo.create_message(s.id, MessageRole.USER, f"msg-{i}")

        msgs = await repo.get_messages(s.id, limit=3)
        assert len(msgs) == 3

    async def test_touch_session_updates_updated_at(self, repo, user_id, db_session):
        s = await repo.create_session(user_id=user_id)
        original_updated_at = s.updated_at

        await asyncio.sleep(0.01)
        await repo.touch_session(s.id)

        await db_session.refresh(s)
        assert s.updated_at > original_updated_at

    async def test_models_are_sqlalchemy(self):
        """ChatSession/ChatMessage가 SQLAlchemy 모델이어야 함."""
        assert issubclass(ChatSession, Base)
        assert issubclass(ChatMessage, Base)
