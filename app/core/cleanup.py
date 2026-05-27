import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.db.sqlalchemy_client import _AsyncSessionFactory
from app.models.ocr.ocr_document import OcrDocument

logger = logging.getLogger(__name__)

_EXPIRY_DAYS = 30


def _delete_local_file(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info("Cleanup: removed local file %s", path)
    except OSError as exc:
        logger.error("Cleanup: failed to remove local file %s: %s", path, exc)


async def cleanup_expired_documents() -> None:
    cutoff = datetime.now(tz=UTC) - timedelta(days=_EXPIRY_DAYS)
    async with _AsyncSessionFactory() as session:
        result = await session.execute(
            select(OcrDocument).where(
                OcrDocument.is_active.is_(False),
                OcrDocument.deleted_at <= cutoff,
            )
        )
        docs = result.scalars().all()

        if not docs:
            logger.info("Cleanup: no expired documents")
            return

        logger.info("Cleanup: %d expired document(s) found", len(docs))
        for doc in docs:
            try:
                if doc.s3_bucket == "__local__":
                    _delete_local_file(doc.s3_key)
                await session.delete(doc)
                await session.commit()
                logger.info("Cleanup: hard-deleted record_id=%s", doc.record_id)
            except Exception as exc:
                await session.rollback()
                logger.error("Cleanup: failed record_id=%s error=%s", doc.record_id, exc)


async def run_cleanup_loop() -> None:
    while True:
        try:
            await cleanup_expired_documents()
        except Exception as exc:
            logger.error("Cleanup loop error: %s", exc)
        await asyncio.sleep(60 * 60 * 24)
