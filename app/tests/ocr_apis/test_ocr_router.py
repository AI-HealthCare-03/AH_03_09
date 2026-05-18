from unittest.mock import AsyncMock, patch


class TestOcrHealth:
    def test_health_check(self, client):
        """OCR 헬스체크 — 인증 불필요"""
        response = client.get("/api/v1/ocr/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestOcrAuth:
    def test_list_records_unauthenticated(self, client):
        """JWT 없이 문서 목록 조회 → 401/403 (인증 차단)"""
        response = client.get("/api/v1/ocr/records")
        assert response.status_code in (401, 403)

    def test_get_job_status_unauthenticated(self, client):
        """JWT 없이 job 상태 조회 → 401/403"""
        response = client.get("/api/v1/ocr/jobs/00000000-0000-0000-0000-000000000000/status")
        assert response.status_code in (401, 403)

    def test_upload_unauthenticated(self, client):
        """JWT 없이 업로드 → 401/403"""
        response = client.post("/api/v1/ocr/upload")
        assert response.status_code in (401, 403)

    def test_list_records_authenticated(self, client, mock_db, auth_headers):
        """JWT 인증 후 문서 목록 조회 → 200 (빈 목록)"""
        mock_db.execute.return_value.fetchone.return_value = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "kakao_id": "123456789",
            "email": "test@example.com",
            "nickname": "테스트유저",
            "profile_image": None,
            "location": None,
            "created_at": "2026-01-01T00:00:00+00:00",
        }

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.list_documents = AsyncMock(return_value=[])
            response = client.get("/api/v1/ocr/records", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["documents"] == []
