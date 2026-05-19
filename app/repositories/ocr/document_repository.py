import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ocr.ocr_document import OcrDocument


class OcrDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, document: OcrDocument) -> OcrDocument:
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        return document

    async def get_by_record_id(self, record_id: int, user_id: uuid.UUID) -> OcrDocument | None:
        result = await self.session.execute(
            select(OcrDocument)
            .options(
                selectinload(OcrDocument.result),
                selectinload(OcrDocument.medications),
                selectinload(OcrDocument.disease_codes),
            )
            .where(
                OcrDocument.record_id == record_id,
                OcrDocument.user_id == user_id,
                OcrDocument.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_job_id(self, job_id: uuid.UUID, user_id: uuid.UUID) -> OcrDocument | None:
        result = await self.session.execute(
            select(OcrDocument)
            .options(selectinload(OcrDocument.result))
            .where(
                OcrDocument.job_id == job_id,
                OcrDocument.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_file_hash(self, user_id: uuid.UUID, file_hash: str) -> OcrDocument | None:
        result = await self.session.execute(
            select(OcrDocument).where(
                OcrDocument.user_id == user_id,
                OcrDocument.file_hash == file_hash,
                OcrDocument.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[OcrDocument]:
        result = await self.session.execute(
            select(OcrDocument)
            .where(OcrDocument.user_id == user_id, OcrDocument.is_active.is_(True))
            .order_by(OcrDocument.created_at.desc())
        )
        return list(result.scalars().all())
