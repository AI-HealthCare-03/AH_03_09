from unittest.mock import AsyncMock, MagicMock, patch


class TestWithdrawMe:
    def test_withdraw_success(self, client, auth_headers):
        """회원탈퇴 정상 케이스 → 204 + soft_delete 호출 검증."""
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
                "app.repositories.user_repository.UserRepository.soft_delete",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_soft_delete,
        ):
            response = client.delete("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 204
        mock_soft_delete.assert_awaited_once_with(1)

    def test_withdraw_unauthenticated(self, client):
        """인증 헤더 없이 호출 → 401 (HTTPBearer 기본 동작)."""
        response = client.delete("/api/v1/users/me")
        assert response.status_code == 401

    def test_withdraw_inactive_user_rejected(self, client, auth_headers):
        """이미 탈퇴한 사용자(get_user가 None 반환)는 401."""
        with patch(
            "app.repositories.user_repository.UserRepository.get_user",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.delete("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 401
