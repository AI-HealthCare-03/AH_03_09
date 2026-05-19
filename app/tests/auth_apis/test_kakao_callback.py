from unittest.mock import AsyncMock, MagicMock, patch


class TestKakaoCallback:
    def test_kakao_login_url(self, client):
        """카카오 로그인 URL 반환 테스트"""
        response = client.get("/api/v1/auth/kakao/login")
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "kauth.kakao.com/oauth/authorize" in data["auth_url"]

    def test_kakao_callback_success(self, client):
        """카카오 콜백 성공 — JWT 발급 테스트.

        UserRepository.upsert_kakao_user를 직접 mock 해서 DB 없이도 통과하게 한다.
        """
        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {"access_token": "kakao_token_abc"}

        mock_user_resp = MagicMock()
        mock_user_resp.status_code = 200
        mock_user_resp.json.return_value = {
            "id": 123456789,
            "kakao_account": {
                "email": "test@kakao.com",
                "name": "테스트유저",
            },
        }

        fake_user = MagicMock()
        fake_user.id = 1

        with (
            patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_token_resp),
            patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_user_resp),
            patch(
                "app.repositories.user_repository.UserRepository.upsert_kakao_user",
                new_callable=AsyncMock,
                return_value=fake_user,
            ),
        ):
            response = client.post("/api/v1/auth/kakao/callback", params={"code": "test_code"})

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_kakao_callback_invalid_code(self, client):
        """잘못된 code → 400 반환 테스트"""
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"error": "invalid_grant"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            response = client.post("/api/v1/auth/kakao/callback", params={"code": "bad_code"})

        assert response.status_code == 400
