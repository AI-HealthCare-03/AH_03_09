import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.main import app
from app.models.base import Base


@pytest.fixture(scope="session")
def client():
    """TestClient를 `with` 없이 반환해 lifespan(DB 연결)을 건너뛴다.
    DB 호출이 필요한 라우터 단위 테스트는 Repository를 직접 mock 한다."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """UserRepository.get_user를 mock해서 DB 없이 JWT 인증을 통과시킨다."""
    fake_user = MagicMock()
    fake_user.id = 1

    with patch(
        "app.repositories.user_repository.UserRepository.get_user",
        new_callable=AsyncMock,
        return_value=fake_user,
    ):
        yield MagicMock()


@pytest.fixture
def mock_openai():
    with patch("app.services.chat._openai") as mock:
        choice = MagicMock()
        choice.message.content = (
            "두통은 긴장성 두통일 수 있습니다. 충분한 휴식을 취하시고 증상이 지속되면 전문의 상담을 권고합니다."
        )
        mock.chat.completions.create.return_value = MagicMock(choices=[choice])
        yield mock


@pytest.fixture
def sample_user_payload():
    """JWT 발급용 user-like 객체 — Tortoise 인스턴스가 아닌 단순 dict."""
    return {"id": 1, "kakao_id": "123456789", "email": "test@example.com"}


@pytest.fixture
def auth_headers(sample_user_payload):
    from app.services.jwt import JwtService

    user = MagicMock()
    user.id = sample_user_payload["id"]
    tokens = JwtService().issue_jwt_pair(user)
    return {"Authorization": f"Bearer {str(tokens['access_token'])}"}


# ── Integration test fixtures (real Postgres via testcontainers) ─────────────


@pytest.fixture(scope="session")
def postgres_url():
    """CI 환경(TEST_DATABASE_URL 설정 시) 기존 서비스 DB 사용, 로컬은 testcontainers로 자동 실행."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
    else:
        with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
            yield pg.get_connection_url()


@pytest.fixture
async def db_session(postgres_url):
    """테스트마다 모든 SQLAlchemy 테이블을 생성/삭제해 격리."""
    engine = create_async_engine(postgres_url)
    async with engine.begin() as conn:
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
