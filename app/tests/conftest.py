from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_db():
    """psycopg3 ConnectionPool mock — get_pool().connection() 컨텍스트 매니저 모사"""
    with patch("app.core.db.postgres_client._pool") as mock_pool:
        mock_conn = MagicMock()
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_conn


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
def sample_user():
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "kakao_id": "123456789",
        "email": "test@example.com",
        "nickname": "테스트유저",
        "profile_image": None,
        "location": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.fixture
def auth_headers(sample_user):
    from app.models.users import User
    from app.services.jwt import JwtService

    user = User(**sample_user)
    tokens = JwtService().issue_jwt_pair(user)
    return {"Authorization": f"Bearer {str(tokens['access_token'])}"}
