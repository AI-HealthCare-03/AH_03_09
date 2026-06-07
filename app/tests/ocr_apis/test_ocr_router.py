import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

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
    doc.original_filename = "test.jpg"
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
            mock_svc.return_value.list_documents = AsyncMock(return_value=([], 0))
            response = client.get("/api/v1/ocr/records", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["documents"] == []


class TestOcrUpload:
    def test_upload_success(self, client, mock_db, auth_headers):
        """유효한 이미지 단일 업로드 → 202, uploaded_files 배열 반환 (REQ-OCR-002)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.repo.count_today_uploads = AsyncMock(return_value=0)
            mock_svc.return_value.upload_document = AsyncMock(return_value=_mock_doc())
            response = client.post(
                "/api/v1/ocr/upload",
                headers=auth_headers,
                files=[("files", ("test.jpg", b"fake-jpeg-content", "image/jpeg"))],
            )

        assert response.status_code == 202
        data = response.json()
        assert "uploaded_files" in data
        assert len(data["uploaded_files"]) == 1
        assert data["uploaded_files"][0]["record_id"] == 1
        assert data["uploaded_files"][0]["ocr_status"] == "PENDING"
        assert "job_id" in data["uploaded_files"][0]

    def test_upload_multiple_files(self, client, mock_db, auth_headers):
        """2개 파일 업로드 시도 → 422 (1개 제한)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        response = client.post(
            "/api/v1/ocr/upload",
            headers=auth_headers,
            files=[
                ("files", ("a.jpg", b"content-a", "image/jpeg")),
                ("files", ("b.png", b"content-b", "image/png")),
            ],
        )

        assert response.status_code == 422

    def test_upload_too_many_files(self, client, mock_db, auth_headers):
        """2개 파일 업로드 시도 → 422 (1개 제한)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        response = client.post(
            "/api/v1/ocr/upload",
            headers=auth_headers,
            files=[("files", (f"f{i}.jpg", b"x", "image/jpeg")) for i in range(2)],
        )

        assert response.status_code == 422

    def test_upload_png(self, client, mock_db, auth_headers):
        """PNG 파일 업로드 → 202 (REQ-OCR-002 허용 형식)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.repo.count_today_uploads = AsyncMock(return_value=0)
            mock_svc.return_value.upload_document = AsyncMock(return_value=_mock_doc())
            response = client.post(
                "/api/v1/ocr/upload",
                headers=auth_headers,
                files=[("files", ("test.png", b"fake-png-content", "image/png"))],
            )

        assert response.status_code == 202

    def test_upload_pdf(self, client, mock_db, auth_headers):
        """PDF 파일 업로드 → 202 (REQ-OCR-002 허용 형식)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.repo.count_today_uploads = AsyncMock(return_value=0)
            mock_svc.return_value.upload_document = AsyncMock(return_value=_mock_doc())
            response = client.post(
                "/api/v1/ocr/upload",
                headers=auth_headers,
                files=[("files", ("test.pdf", b"fake-pdf-content", "application/pdf"))],
            )

        assert response.status_code == 202

    def test_upload_pdf_too_many_pages(self, client, mock_db, auth_headers):
        """PDF 3페이지 업로드 → 422 (REQ-OCR-026 최대 2페이지)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.services.ocr.file_validator.PdfReader") as mock_reader:
            mock_reader.return_value.pages = [MagicMock()] * 3
            response = client.post(
                "/api/v1/ocr/upload",
                headers=auth_headers,
                files=[("files", ("test.pdf", b"%PDF-1.4 fake", "application/pdf"))],
            )

        assert response.status_code == 422
        assert "2페이지" in response.json()["detail"]

    def test_upload_invalid_mime_type(self, client, mock_db, auth_headers):
        """허용되지 않는 파일 형식 → 422 (REQ-OCR-002)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        response = client.post(
            "/api/v1/ocr/upload",
            headers=auth_headers,
            files=[("files", ("test.txt", b"text content", "text/plain"))],
        )

        assert response.status_code == 422

    def test_upload_extension_mismatch(self, client, mock_db, auth_headers):
        """MIME 타입과 확장자 불일치 → 422 (REQ-OCR-002 이중 검증)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        response = client.post(
            "/api/v1/ocr/upload",
            headers=auth_headers,
            files=[("files", ("fake.png", b"content", "image/jpeg"))],
        )

        assert response.status_code == 422

    def test_upload_empty_file(self, client, mock_db, auth_headers):
        """빈 파일 업로드 → 422 (REQ-OCR-002)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        response = client.post(
            "/api/v1/ocr/upload",
            headers=auth_headers,
            files=[("files", ("empty.jpg", b"", "image/jpeg"))],
        )

        assert response.status_code == 422

    def test_upload_oversized_file(self, client, mock_db, auth_headers):
        """10MB 초과 파일 → 422 (REQ-OCR-002)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW
        big_content = b"x" * (10 * 1024 * 1024 + 1)

        response = client.post(
            "/api/v1/ocr/upload",
            headers=auth_headers,
            files=[("files", ("big.jpg", big_content, "image/jpeg"))],
        )

        assert response.status_code == 422

    def test_upload_duplicate_file(self, client, mock_db, auth_headers):
        """중복 파일(동일 SHA-256) → 409 (REQ-OCR-002)"""
        from fastapi import HTTPException

        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.repo.count_today_uploads = AsyncMock(return_value=0)
            mock_svc.return_value.upload_document = AsyncMock(
                side_effect=HTTPException(
                    status_code=409,
                    detail={"message": "이미 업로드된 파일입니다.", "existing_record_id": 1},
                )
            )
            response = client.post(
                "/api/v1/ocr/upload",
                headers=auth_headers,
                files=[("files", ("test.jpg", b"fake-jpeg-content", "image/jpeg"))],
            )

        assert response.status_code == 409


class TestOcrRecordFile:
    def test_get_file_success(self, client, mock_db, auth_headers, tmp_path):
        """원본 파일 서빙 → 200, 파일 내용 반환"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW
        fake_file = tmp_path / "test.jpg"
        fake_file.write_bytes(b"fake-jpeg-content")

        from fastapi.responses import FileResponse

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.get_file_response = AsyncMock(
                return_value=FileResponse(str(fake_file), media_type="image/jpeg")
            )
            response = client.get("/api/v1/ocr/records/1/file", headers=auth_headers)

        assert response.status_code == 200
        assert response.content == b"fake-jpeg-content"

    def test_get_file_not_found(self, client, mock_db, auth_headers):
        """존재하지 않는 문서 → 404"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            from fastapi import HTTPException

            mock_svc.return_value.get_file_response = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
            )
            response = client.get("/api/v1/ocr/records/999/file", headers=auth_headers)

        assert response.status_code == 404


class TestOcrDeleteRecord:
    def test_delete_success(self, client, mock_db, auth_headers):
        """문서 소프트 삭제 → 204"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.delete_document = AsyncMock(return_value=None)
            response = client.delete("/api/v1/ocr/records/1", headers=auth_headers)

        assert response.status_code == 204

    def test_delete_not_found(self, client, mock_db, auth_headers):
        """존재하지 않는 문서 삭제 → 404"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            from fastapi import HTTPException

            mock_svc.return_value.delete_document = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
            )
            response = client.delete("/api/v1/ocr/records/999", headers=auth_headers)

        assert response.status_code == 404

    def test_delete_processing(self, client, mock_db, auth_headers):
        """OCR 처리 중인 문서 삭제 → 409"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            from fastapi import HTTPException

            mock_svc.return_value.delete_document = AsyncMock(
                side_effect=HTTPException(status_code=409, detail="처리 중인 문서는 삭제할 수 없습니다.")
            )
            response = client.delete("/api/v1/ocr/records/1", headers=auth_headers)

        assert response.status_code == 409


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
        assert data["status"] == "PENDING"
        assert data["record_id"] == 1
        assert "progress_pct" in data
        assert "message" in data

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

    def test_get_job_status_low_confidence_sets_retake_recommended(self, client, mock_db, auth_headers):
        """DONE + confidence < 0.7 → retake_recommended=True (REQ-OCR-020)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW
        job_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")

        doc = _mock_doc()
        doc.ocr_status = "DONE"
        doc.result = MagicMock()
        doc.result.confidence_score = 0.55

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.get_job_status = AsyncMock(return_value=doc)
            response = client.get(f"/api/v1/ocr/jobs/{job_id}/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["retake_recommended"] is True
        assert "재촬영" in data["message"]

    def test_get_job_status_high_confidence_no_retake(self, client, mock_db, auth_headers):
        """DONE + confidence >= 0.7 → retake_recommended=False (REQ-OCR-020)"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW
        job_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")

        doc = _mock_doc()
        doc.ocr_status = "DONE"
        doc.result = MagicMock()
        doc.result.confidence_score = 0.92

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.get_job_status = AsyncMock(return_value=doc)
            response = client.get(f"/api/v1/ocr/jobs/{job_id}/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["retake_recommended"] is False


class TestOcrConfirm:
    def test_confirm_without_triggers_returns_200(self, client, mock_db, auth_headers):
        """trigger 없이 confirm → 200, guide_job_id=None"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW
        job_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.confirm_document = AsyncMock(return_value=(1, job_id, None))
            response = client.post(
                f"/api/v1/ocr/jobs/{job_id}/confirm",
                json={"trigger_guide": False, "trigger_chatbot_context": False},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == 1
        assert data["guide_job_id"] is None

    def test_confirm_with_trigger_guide_returns_guide_job_id(self, client, mock_db, auth_headers):
        """trigger_guide=True → guide_job_id 반환"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW
        job_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.confirm_document = AsyncMock(return_value=(1, job_id, "guide-job-abc123"))
            response = client.post(
                f"/api/v1/ocr/jobs/{job_id}/confirm",
                json={"trigger_guide": True, "trigger_chatbot_context": False},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["guide_job_id"] == "guide-job-abc123"

    def test_confirm_not_done_returns_409(self, client, mock_db, auth_headers):
        """DONE 아닌 문서 confirm → 409"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW
        job_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.confirm_document = AsyncMock(
                side_effect=HTTPException(status_code=409, detail="OCR 처리가 완료된 문서만 확인할 수 있습니다.")
            )
            response = client.post(
                f"/api/v1/ocr/jobs/{job_id}/confirm",
                json={"trigger_guide": False, "trigger_chatbot_context": False},
                headers=auth_headers,
            )

        assert response.status_code == 409

    def test_confirm_unauthenticated_returns_401(self, client):
        """인증 없이 confirm → 401/403"""
        job_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
        response = client.post(f"/api/v1/ocr/jobs/{job_id}/confirm", json={})
        assert response.status_code in (401, 403)


class TestUpdateDiseaseCode:
    def test_update_disease_code_success(self, client, mock_db, auth_headers):
        """ICD-10 코드 수정 성공 → 200 + 갱신된 disease_name 반환"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW
        mock_code = MagicMock()
        mock_code.id = 1
        mock_code.icd10_code = "J30.1"
        mock_code.disease_name = "알레르기비염"
        mock_code.confidence_score = None
        mock_code.is_confirmed = False
        mock_code.is_active = True

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.update_disease_code = AsyncMock(return_value=mock_code)
            response = client.patch(
                "/api/v1/ocr/records/1/disease-codes/1",
                json={"icd10_code": "J30.1"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json()["icd10_code"] == "J30.1"
        assert response.json()["disease_name"] == "알레르기비염"

    def test_update_disease_code_not_found(self, client, mock_db, auth_headers):
        """존재하지 않는 질병코드 수정 → 404"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.update_disease_code = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="질병분류기호를 찾을 수 없습니다.")
            )
            response = client.patch(
                "/api/v1/ocr/records/1/disease-codes/999",
                json={"icd10_code": "J30.1"},
                headers=auth_headers,
            )

        assert response.status_code == 404

    def test_update_disease_code_missing_code(self, client, mock_db, auth_headers):
        """icd10_code 없이 요청 → 422"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.update_disease_code = AsyncMock()
            response = client.patch(
                "/api/v1/ocr/records/1/disease-codes/1",
                json={},
                headers=auth_headers,
            )

        assert response.status_code == 422


class TestConfirmMedications:
    def test_confirm_medications_success(self, client, mock_db, auth_headers):
        """약물 전체 확인 처리 → 200 + confirmed_count"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.confirm_medications = AsyncMock(return_value=3)
            response = client.post("/api/v1/ocr/records/1/medications/confirm", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["confirmed_count"] == 3

    def test_confirm_medications_not_found(self, client, mock_db, auth_headers):
        """존재하지 않는 문서 → 404"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.confirm_medications = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
            )
            response = client.post("/api/v1/ocr/records/999/medications/confirm", headers=auth_headers)

        assert response.status_code == 404

    def test_confirm_medications_unauthenticated(self, client):
        """인증 없이 요청 → 401/403"""
        response = client.post("/api/v1/ocr/records/1/medications/confirm")
        assert response.status_code in (401, 403)


class TestConfirmDiseaseCodes:
    def test_confirm_disease_codes_success(self, client, mock_db, auth_headers):
        """질병코드 전체 확인 처리 → 200 + confirmed_count"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.confirm_disease_codes = AsyncMock(return_value=2)
            response = client.post("/api/v1/ocr/records/1/disease-codes/confirm", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["confirmed_count"] == 2

    def test_confirm_disease_codes_not_found(self, client, mock_db, auth_headers):
        """존재하지 않는 문서 → 404"""
        mock_db.execute.return_value.fetchone.return_value = _USER_ROW

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.confirm_disease_codes = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
            )
            response = client.post("/api/v1/ocr/records/999/disease-codes/confirm", headers=auth_headers)

        assert response.status_code == 404
