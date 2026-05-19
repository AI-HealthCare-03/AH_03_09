import uuid
from unittest.mock import AsyncMock, MagicMock, patch

_USER_ROW = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "kakao_id": "123456789",
    "email": "test@example.com",
    "nickname": "테스트유저",
    "profile_image": None,
    "location": None,
    "created_at": "2026-01-01T00:00:00+00:00",
}


def _mock_doc(record_id: int = 1) -> MagicMock:
    doc = MagicMock()
    doc.record_id = record_id
    doc.job_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
    doc.ocr_status = "PENDING"
    doc.result = None
    return doc


class TestOcrHealth:
    def test_health_check(self, client):
        """OCR 헬스체크 — 인증 불필요"""
        response = client.get("/api/v1/ocr/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestOcrAuth:
    def test_list_records_unauthenticated(self, client):
        """JWT 없이 문서 목록 조회 → 401/403"""
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
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.list_documents = AsyncMock(return_value=[])
            response = client.get("/api/v1/ocr/records", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["documents"] == []


class TestOcrUpload:
    def test_upload_success(self, client, mock_db, auth_headers):
        """유효한 이미지 업로드 → 202, record_id + job_id + PENDING 반환 (REQ-OCR-001)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.upload_document = AsyncMock(return_value=_mock_doc())
            response = client.post(
                "/api/v1/ocr/upload",
                headers=auth_headers,
                files={"file": ("test.jpg", b"fake-jpeg-content", "image/jpeg")},
            )

        assert response.status_code == 202
        data = response.json()
        assert data["record_id"] == 1
        assert data["ocr_status"] == "PENDING"
        assert "job_id" in data

    def test_upload_png(self, client, mock_db, auth_headers):
        """PNG 파일 업로드 → 202 (REQ-OCR-002 허용 형식)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.upload_document = AsyncMock(return_value=_mock_doc())
            response = client.post(
                "/api/v1/ocr/upload",
                headers=auth_headers,
                files={"file": ("test.png", b"fake-png-content", "image/png")},
            )

        assert response.status_code == 202

    def test_upload_pdf(self, client, mock_db, auth_headers):
        """PDF 파일 업로드 → 202 (REQ-OCR-002 허용 형식)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.upload_document = AsyncMock(return_value=_mock_doc())
            response = client.post(
                "/api/v1/ocr/upload",
                headers=auth_headers,
                files={"file": ("test.pdf", b"fake-pdf-content", "application/pdf")},
            )

        assert response.status_code == 202

    def test_upload_invalid_mime_type(self, client, mock_db, auth_headers):
        """허용되지 않는 파일 형식 → 422 (REQ-OCR-002)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        response = client.post(
            "/api/v1/ocr/upload",
            headers=auth_headers,
            files={"file": ("test.txt", b"text content", "text/plain")},
        )

        assert response.status_code == 422

    def test_upload_empty_file(self, client, mock_db, auth_headers):
        """빈 파일 업로드 → 422 (REQ-OCR-002)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        response = client.post(
            "/api/v1/ocr/upload",
            headers=auth_headers,
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )

        assert response.status_code == 422

    def test_upload_oversized_file(self, client, mock_db, auth_headers):
        """10MB 초과 파일 → 422 (REQ-OCR-002)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW
        big_content = b"x" * (10 * 1024 * 1024 + 1)

        response = client.post(
            "/api/v1/ocr/upload",
            headers=auth_headers,
            files={"file": ("big.jpg", big_content, "image/jpeg")},
        )

        assert response.status_code == 422


class TestOcrJobStatus:
    def test_get_job_status_success(self, client, mock_db, auth_headers):
        """인증된 유저가 본인 job 상태 조회 → 200 (REQ-OCR-004)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW
        job_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.get_job_status = AsyncMock(return_value=_mock_doc())
            response = client.get(f"/api/v1/ocr/jobs/{job_id}/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["ocr_status"] == "PENDING"
        assert data["record_id"] == 1

    def test_get_job_status_not_found(self, client, mock_db, auth_headers):
        """존재하지 않는 job → 404 (REQ-OCR-004)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW
        job_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            from fastapi import HTTPException

            mock_svc.return_value.get_job_status = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
            )
            response = client.get(f"/api/v1/ocr/jobs/{job_id}/status", headers=auth_headers)

        assert response.status_code == 404
