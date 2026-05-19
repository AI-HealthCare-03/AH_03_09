import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    """TestClient를 `with` 없이 반환해 lifespan(Tortoise.init/DB 연결)을 건너뛴다.
    DB 호출이 필요한 테스트는 Repository를 직접 mock 한다."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """UserRepository.get_user를 mock해서 DB 없이 JWT 인증을 통과시킨다.
    OCR 라우터가 uuid.UUID(str(current_user.id))를 호출하므로 id는 UUID 타입으로 설정."""
    fake_user = MagicMock()
    fake_user.id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

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
