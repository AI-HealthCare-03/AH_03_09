CONV_ID = "conv-uuid-1234"
USER_ID = "550e8400-e29b-41d4-a716-446655440000"
SAMPLE_CONV = {
    "id": CONV_ID,
    "user_id": USER_ID,
    "title": "새 대화",
    "created_at": "2026-01-01T00:00:00+00:00",
}
SAMPLE_USER_MSG = {
    "id": "msg-uuid-0",
    "conversation_id": CONV_ID,
    "role": "user",
    "content": "두통이 자주 있어요",
    "embedding": None,
    "created_at": "2026-01-01T00:00:01+00:00",
}
SAMPLE_MSG = {
    "id": "msg-uuid-1",
    "conversation_id": CONV_ID,
    "role": "assistant",
    "content": "두통은 긴장성 두통일 수 있습니다. 전문의 상담을 권고합니다.",
    "embedding": None,
    "created_at": "2026-01-01T00:00:02+00:00",
}
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
        """새 대화 생성 테스트"""
        mock_db.execute.return_value.fetchone.side_effect = [SAMPLE_USER, SAMPLE_CONV]

        response = client.post(
            "/api/v1/chat/conversations",
            json={"title": "새 대화"},
            headers=auth_headers,
        )
        assert response.status_code == 201

    def test_send_message_normal(self, client, mock_db, mock_openai, auth_headers):
        """정상 메시지 전송 + E-O 루프 PASS 테스트"""
        # fetchone 호출 순서: get_user, get_conversation, create_message(user), create_message(assistant)
        mock_db.execute.return_value.fetchone.side_effect = [SAMPLE_USER, SAMPLE_CONV, SAMPLE_USER_MSG, SAMPLE_MSG]
        mock_db.execute.return_value.fetchall.return_value = []

        response = client.post(
            f"/api/v1/chat/conversations/{CONV_ID}/messages",
            json={"content": "두통이 자주 있어요"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_send_message_danger_keyword(self, client, mock_db, auth_headers):
        """위험 키워드 입력 시 EMERGENCY_RESPONSE 반환 테스트"""
        emergency_msg = {**SAMPLE_MSG, "content": "⚠️ 응급 상황이 의심됩니다."}
        mock_db.execute.return_value.fetchone.side_effect = [SAMPLE_USER, SAMPLE_CONV, emergency_msg]

        response = client.post(
            f"/api/v1/chat/conversations/{CONV_ID}/messages",
            json={"content": "자살하고 싶어요"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "응급" in response.json().get("content", "")

    def test_get_conversation_not_found(self, client, mock_db, auth_headers):
        """존재하지 않는 대화 조회 → 404 테스트"""
        mock_db.execute.return_value.fetchone.side_effect = [SAMPLE_USER, None]

        response = client.get(
            "/api/v1/chat/conversations/nonexistent-id",
            headers=auth_headers,
        )
        assert response.status_code == 404
