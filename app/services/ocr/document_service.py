import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocr.ocr_document import OcrDocument
from app.repositories.ocr.document_repository import OcrDocumentRepository


class OcrDocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = OcrDocumentRepository(session)

    async def list_documents(self, user_id: uuid.UUID) -> list[OcrDocument]:
        return await self.repo.list_by_user(user_id)

    async def get_document(self, record_id: int, user_id: uuid.UUID) -> OcrDocument:
        doc = await self.repo.get_by_record_id(record_id, user_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다.")
        return doc

    async def get_job_status(self, job_id: uuid.UUID, user_id: uuid.UUID) -> OcrDocument:
        doc = await self.repo.get_by_job_id(job_id, user_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")
        return doc
