from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

CONV_ID = "550e8400-e29b-41d4-a716-446655440001"
USER_ID = "550e8400-e29b-41d4-a716-446655440000"
SAMPLE_USER = {
    "id": USER_ID,
    "kakao_id": "123456789",
    "nickname": "테스트",
    "email": None,
    "profile_image": None,
    "location": None,
    "created_at": "2026-01-01T00:00:00+00:00",
}


class TestChatConversations:
    def test_create_conversation(self, client, mock_db, auth_headers):
        """새 세션 생성 테스트"""
        mock_db.execute.return_value.fetchone.return_value = SAMPLE_USER

        mock_session = MagicMock()
        mock_session.id = UUID(CONV_ID)
        mock_session.title = "새 대화"
        mock_session.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        mock_session.updated_at = datetime(2026, 1, 1, tzinfo=UTC)

        with patch("app.apis.v1.chat_routers.ChatService") as mock_chat_service:
            mock_chat_service.return_value.create_session = AsyncMock(return_value=mock_session)
            response = client.post(
                "/api/v1/chat/sessions",
                json={"title": "새 대화"},
                headers=auth_headers,
            )

        assert response.status_code == 201

    @pytest.mark.skip(reason="메시지 전송은 WebSocket 전용 — HTTP POST 엔드포인트 없음")
    def test_send_message_normal(self, client, mock_db, auth_headers):
        pass

    @pytest.mark.skip(reason="메시지 전송은 WebSocket 전용 — HTTP POST 엔드포인트 없음")
    def test_send_message_danger_keyword(self, client, mock_db, auth_headers):
        pass

    def test_get_conversation_not_found(self, client, mock_db, auth_headers):
        """존재하지 않는 세션 메시지 조회 → 404 테스트"""
        mock_db.execute.return_value.fetchone.return_value = SAMPLE_USER

        with patch("app.apis.v1.chat_routers.ChatService") as mock_chat_service:
            mock_chat_service.return_value.get_session_messages = AsyncMock(return_value=None)
            response = client.get(
                f"/api/v1/chat/sessions/{CONV_ID}/messages",
                headers=auth_headers,
            )

        assert response.status_code == 404
