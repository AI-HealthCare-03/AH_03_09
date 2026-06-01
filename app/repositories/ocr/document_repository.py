import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ocr.ocr_document import DiseaseCode, Medication, OcrDocument


class OcrDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, document: OcrDocument) -> OcrDocument:
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        return document

    async def get_by_record_id(self, record_id: int, user_id: int) -> OcrDocument | None:
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

    async def get_by_job_id(self, job_id: uuid.UUID, user_id: int) -> OcrDocument | None:
        result = await self.session.execute(
            select(OcrDocument)
            .options(selectinload(OcrDocument.result))
            .where(
                OcrDocument.job_id == job_id,
                OcrDocument.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_job_id_with_medications(self, job_id: uuid.UUID, user_id: int) -> OcrDocument | None:
        result = await self.session.execute(
            select(OcrDocument)
            .options(
                selectinload(OcrDocument.result),
                selectinload(OcrDocument.medications),
                selectinload(OcrDocument.disease_codes),
            )
            .where(
                OcrDocument.job_id == job_id,
                OcrDocument.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_file_hash(self, user_id: int, file_hash: str) -> OcrDocument | None:
        result = await self.session.execute(
            select(OcrDocument).where(
                OcrDocument.user_id == user_id,
                OcrDocument.file_hash == file_hash,
                OcrDocument.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def soft_delete(self, record_id: int, user_id: int) -> OcrDocument | None:
        result = await self.session.execute(
            select(OcrDocument).where(
                OcrDocument.record_id == record_id,
                OcrDocument.user_id == user_id,
                OcrDocument.is_active.is_(True),
            )
        )
        doc = result.scalar_one_or_none()
        if doc is not None:
            doc.is_active = False
            await self.session.flush()
        return doc

    async def count_today_uploads(self, user_id: int) -> int:
        today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=UTC)
        result = await self.session.execute(
            select(func.count())
            .select_from(OcrDocument)
            .where(
                OcrDocument.user_id == user_id,
                OcrDocument.created_at >= today_start,
            )
        )
        return result.scalar_one()

    async def add_medication(
        self,
        document_id: int,
        medication_name: str,
        frequency: str | None,
        duration_days: int | None,
    ) -> Medication:
        med = Medication(
            document_id=document_id,
            medication_name=medication_name,
            frequency=frequency,
            duration_days=duration_days,
        )
        self.session.add(med)
        await self.session.flush()
        await self.session.refresh(med)
        return med

    async def get_medication(self, record_id: int, medication_id: int, user_id: int) -> Medication | None:
        result = await self.session.execute(
            select(Medication)
            .join(OcrDocument, Medication.document_id == OcrDocument.record_id)
            .where(
                Medication.id == medication_id,
                Medication.document_id == record_id,
                Medication.is_active.is_(True),
                OcrDocument.user_id == user_id,
                OcrDocument.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_disease_code(self, record_id: int, disease_code_id: int, user_id: int) -> DiseaseCode | None:
        result = await self.session.execute(
            select(DiseaseCode)
            .join(OcrDocument, DiseaseCode.document_id == OcrDocument.record_id)
            .where(
                DiseaseCode.id == disease_code_id,
                DiseaseCode.document_id == record_id,
                DiseaseCode.is_active.is_(True),
                OcrDocument.user_id == user_id,
                OcrDocument.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def confirm_all_medications(self, record_id: int, user_id: int) -> int:
        """문서의 활성 약물 전체를 is_confirmed=True로 일괄 처리합니다. 변경된 행 수를 반환합니다."""
        subq = select(OcrDocument.record_id).where(
            OcrDocument.record_id == record_id,
            OcrDocument.user_id == user_id,
            OcrDocument.is_active.is_(True),
        )
        result = await self.session.execute(
            update(Medication)
            .where(Medication.document_id.in_(subq), Medication.is_active.is_(True))
            .values(is_confirmed=True)
        )
        return result.rowcount

    async def confirm_all_disease_codes(self, record_id: int, user_id: int) -> int:
        """문서의 활성 질병코드 전체를 is_confirmed=True로 일괄 처리합니다. 변경된 행 수를 반환합니다."""
        subq = select(OcrDocument.record_id).where(
            OcrDocument.record_id == record_id,
            OcrDocument.user_id == user_id,
            OcrDocument.is_active.is_(True),
        )
        result = await self.session.execute(
            update(DiseaseCode)
            .where(DiseaseCode.document_id.in_(subq), DiseaseCode.is_active.is_(True))
            .values(is_confirmed=True)
        )
        return result.rowcount

    async def list_by_user(
        self,
        user_id: int,
        doc_type: str | None = None,
        ocr_status: str | None = None,
        sort: str = "created_at_desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[OcrDocument], int]:
        conditions = [OcrDocument.user_id == user_id, OcrDocument.is_active.is_(True)]
        if doc_type:
            conditions.append(OcrDocument.doc_type == doc_type)
        if ocr_status:
            conditions.append(OcrDocument.ocr_status == ocr_status)

        order = OcrDocument.created_at.asc() if sort == "created_at_asc" else OcrDocument.created_at.desc()

        total_result = await self.session.execute(select(func.count()).select_from(OcrDocument).where(*conditions))
        total = total_result.scalar_one()

        result = await self.session.execute(
            select(OcrDocument)
            .options(selectinload(OcrDocument.result))
            .where(*conditions)
            .order_by(order)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total
