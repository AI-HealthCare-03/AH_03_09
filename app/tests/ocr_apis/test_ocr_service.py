import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ocr.document_service import OcrDocumentService


def _make_session():
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _make_doc(record_id: int = 1) -> MagicMock:
    doc = MagicMock()
    doc.record_id = record_id
    doc.job_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
    doc.user_id = 1
    doc.ocr_status = "PENDING"
    doc.original_filename = "test.jpg"
    doc.s3_key = "ocr/user/test.jpg"
    doc.s3_bucket = "test-bucket"
    doc.mime_type = "image/jpeg"
    return doc


class TestUploadDocumentPublishesRedis:
    """upload_document() 호출 시 Redis에 OCR 작업이 발행되는지 검증. (REQ-OCR-024)"""

    @pytest.mark.asyncio
    async def test_publishes_ocr_job_to_redis(self):
        """업로드 성공 시 ocr:request:{job_id} 채널에 payload가 발행된다."""
        session = _make_session()
        doc = _make_doc()

        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()

        with (
            patch("app.services.ocr.document_service.OcrDocumentRepository") as mock_repo_cls,
            patch("app.services.ocr.document_service.S3Service") as mock_s3_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_file_hash = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=doc)
            session.refresh = AsyncMock(side_effect=lambda d: None)

            mock_s3 = mock_s3_cls.return_value
            mock_s3.upload = AsyncMock(return_value=("ocr/user/test.jpg", "https://s3/test.jpg"))

            with patch("app.services.ocr.document_service.S3Service.compute_hash", return_value="abc123"):
                svc = OcrDocumentService(session, redis=mock_redis)
                await svc.upload_document(
                    user_id=1,
                    filename="test.jpg",
                    mime_type="image/jpeg",
                    content=b"fake-content",
                )

        mock_redis.publish.assert_awaited_once()
        channel, raw_payload = mock_redis.publish.call_args.args
        assert channel == f"ocr:request:{doc.job_id}"

        payload = json.loads(raw_payload)
        assert payload["job_id"] == str(doc.job_id)
        assert payload["record_id"] == doc.record_id
        assert payload["mime_type"] == "image/jpeg"

    @pytest.mark.asyncio
    async def test_redis_failure_does_not_raise(self):
        """Redis publish 실패 시 예외를 삼키고 정상 반환한다 (fire-and-forget)."""
        session = _make_session()
        doc = _make_doc()

        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(side_effect=ConnectionError("Redis down"))

        with (
            patch("app.services.ocr.document_service.OcrDocumentRepository") as mock_repo_cls,
            patch("app.services.ocr.document_service.S3Service") as mock_s3_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_file_hash = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=doc)
            session.refresh = AsyncMock(side_effect=lambda d: None)

            mock_s3 = mock_s3_cls.return_value
            mock_s3.upload = AsyncMock(return_value=("ocr/user/test.jpg", "https://s3/test.jpg"))

            with patch("app.services.ocr.document_service.S3Service.compute_hash", return_value="abc123"):
                svc = OcrDocumentService(session, redis=mock_redis)
                result = await svc.upload_document(
                    user_id=1,
                    filename="test.jpg",
                    mime_type="image/jpeg",
                    content=b"fake-content",
                )

        assert result is doc

    @pytest.mark.asyncio
    async def test_duplicate_file_raises_409(self):
        """동일 hash 파일 업로드 시 409 Conflict. (REQ-OCR-002)"""
        from fastapi import HTTPException

        session = _make_session()
        existing = _make_doc(record_id=99)

        with patch("app.services.ocr.document_service.OcrDocumentRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_file_hash = AsyncMock(return_value=existing)

            with patch("app.services.ocr.document_service.S3Service.compute_hash", return_value="dup123"):
                svc = OcrDocumentService(session)
                with pytest.raises(HTTPException) as exc_info:
                    await svc.upload_document(
                        user_id=1,
                        filename="dup.jpg",
                        mime_type="image/jpeg",
                        content=b"dup-content",
                    )

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["existing_record_id"] == 99
