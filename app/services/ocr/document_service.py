import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import config
from app.models.ocr.ocr_document import OcrDocument, OcrStatus
from app.repositories.ocr.document_repository import OcrDocumentRepository
from app.services.ocr.s3_service import S3Service


class OcrDocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OcrDocumentRepository(session)

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
        """S3 업로드 → DB 레코드 생성 → PENDING 상태로 반환. (REQ-OCR-001/003)"""
        s3_svc = S3Service()
        s3_key, file_hash = await s3_svc.upload(
            content=content,
            user_id=user_id,
            mime_type=mime_type,
            original_filename=filename,
        )

        doc = OcrDocument(
            user_id=user_id,
            original_filename=filename,
            s3_key=s3_key,
            s3_bucket=config.AWS_S3_BUCKET_NAME,
            file_hash=file_hash,
            file_size=len(content),
            mime_type=mime_type,
            ocr_status=OcrStatus.PENDING,
        )
        doc = await self.repo.create(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc
