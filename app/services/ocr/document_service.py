import json
import logging
import uuid

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import config
from app.core.redis_client import get_redis
from app.models.ocr.ocr_document import OcrDocument, OcrStatus
from app.repositories.ocr.document_repository import OcrDocumentRepository
from app.services.ocr.s3_service import LOCAL_BUCKET, S3Service

logger = logging.getLogger(__name__)


class OcrDocumentService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis | None = None) -> None:
        self.session = session
        self.repo = OcrDocumentRepository(session)
        self._redis = redis

    async def list_documents(self, user_id: int) -> list[OcrDocument]:
        return await self.repo.list_by_user(user_id)

    async def get_document(self, record_id: int, user_id: int) -> OcrDocument:
        doc = await self.repo.get_by_record_id(record_id, user_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
        return doc

    async def get_job_status(self, job_id: uuid.UUID, user_id: int) -> OcrDocument:
        doc = await self.repo.get_by_job_id(job_id, user_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")
        return doc

    async def upload_document(
        self,
        user_id: int,
        filename: str,
        mime_type: str,
        content: bytes,
    ) -> OcrDocument:
        """중복 검사 → S3 업로드 → DB 레코드 생성 → PENDING 반환. (REQ-OCR-002/003)"""
        file_hash = S3Service.compute_hash(content)

        existing = await self.repo.get_by_file_hash(user_id, file_hash)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "이미 업로드된 파일입니다.",
                    "existing_record_id": existing.record_id,
                },
            )

        s3_svc = S3Service()
        s3_key, _ = await s3_svc.upload(
            content=content,
            user_id=user_id,
            mime_type=mime_type,
            original_filename=filename,
        )

        doc = OcrDocument(
            user_id=user_id,
            original_filename=filename,
            s3_key=s3_key,
            s3_bucket=config.AWS_S3_BUCKET_NAME or LOCAL_BUCKET,
            file_hash=file_hash,
            file_size=len(content),
            mime_type=mime_type,
            ocr_status=OcrStatus.PENDING,
        )
        doc = await self.repo.create(doc)
        await self.session.commit()
        await self.session.refresh(doc)

        await self._publish_ocr_job(doc)

        return doc

    async def _publish_ocr_job(self, doc: OcrDocument) -> None:
        payload = {
            "job_id": str(doc.job_id),
            "record_id": doc.record_id,
            "s3_key": doc.s3_key,
            "s3_bucket": doc.s3_bucket,
            "user_id": doc.user_id,
            "mime_type": doc.mime_type,
            "original_filename": doc.original_filename,
        }
        try:
            redis = self._redis or await get_redis()
            await redis.publish(f"ocr:request:{doc.job_id}", json.dumps(payload))
        except Exception as exc:
            logger.error("Failed to publish OCR job (job_id=%s): %s", doc.job_id, exc)
