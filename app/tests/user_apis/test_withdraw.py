from unittest.mock import AsyncMock, MagicMock, patch


class TestWithdrawMe:
    valid_body = {"confirmation_text": "회원탈퇴합니다"}

    def test_withdraw_success(self, client, auth_headers):
        """회원탈퇴 정상 케이스 → 204 + hard_delete 호출 검증."""
        fake_user = MagicMock()
        fake_user.id = 1
        fake_user.is_active = True

        with (
            patch(
                "app.repositories.user_repository.UserRepository.get_user",
                new_callable=AsyncMock,
                return_value=fake_user,
            ),
            patch(
                "app.repositories.user_repository.UserRepository.hard_delete",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_hard_delete,
        ):
            response = client.request("DELETE", "/api/v1/users/me", headers=auth_headers, json=self.valid_body)

        assert response.status_code == 204
        mock_hard_delete.assert_awaited_once_with(1)

    def test_withdraw_unauthenticated(self, client):
        """인증 헤더 없이 호출 → 401 (HTTPBearer 기본 동작)."""
        response = client.request("DELETE", "/api/v1/users/me", json=self.valid_body)
        assert response.status_code == 401

    def test_withdraw_deleted_user_rejected(self, client, auth_headers):
        """이미 탈퇴(hard_delete)된 사용자(get_user가 None 반환)는 401."""
        with patch(
            "app.repositories.user_repository.UserRepository.get_user",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.request("DELETE", "/api/v1/users/me", headers=auth_headers, json=self.valid_body)

        assert response.status_code == 401

    def test_withdraw_wrong_confirmation_text(self, client, auth_headers):
        """확인 문구가 다르면 400 + hard_delete 미호출."""
        fake_user = MagicMock()
        fake_user.id = 1
        fake_user.is_active = True

        with (
            patch(
                "app.repositories.user_repository.UserRepository.get_user",
                new_callable=AsyncMock,
                return_value=fake_user,
            ),
            patch(
                "app.repositories.user_repository.UserRepository.hard_delete",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_hard_delete,
        ):
            response = client.request(
                "DELETE",
                "/api/v1/users/me",
                headers=auth_headers,
                json={"confirmation_text": "탈퇴"},
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "확인 문구가 일치하지 않습니다."
        mock_hard_delete.assert_not_awaited()

    def test_withdraw_missing_confirmation_text(self, client, auth_headers):
        """body 누락 시 Pydantic 검증으로 422."""
        fake_user = MagicMock()
        fake_user.id = 1
        fake_user.is_active = True

        with patch(
            "app.repositories.user_repository.UserRepository.get_user",
            new_callable=AsyncMock,
            return_value=fake_user,
        ):
            response = client.delete("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 422

    def test_withdraw_empty_confirmation_text(self, client, auth_headers):
        """빈 문자열은 문구 불일치이므로 400."""
        fake_user = MagicMock()
        fake_user.id = 1
        fake_user.is_active = True

        with (
            patch(
                "app.repositories.user_repository.UserRepository.get_user",
                new_callable=AsyncMock,
                return_value=fake_user,
            ),
            patch(
                "app.repositories.user_repository.UserRepository.hard_delete",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_hard_delete,
        ):
            response = client.request(
                "DELETE",
                "/api/v1/users/me",
                headers=auth_headers,
                json={"confirmation_text": ""},
            )

        assert response.status_code == 400
        mock_hard_delete.assert_not_awaited()
