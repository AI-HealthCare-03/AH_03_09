import asyncio
import logging
import time

import asyncpg
import redis.asyncio as aioredis

from ai_worker.core.config import config
from ai_worker.schemas.ocr import OcrTaskPayload

logger = logging.getLogger(__name__)


async def process_ocr(payload: OcrTaskPayload, redis: aioredis.Redis) -> None:
    """OCR 작업 처리: PENDING → PROCESSING → DONE/FAILED. (REQ-OCR-024/025)"""
    conn: asyncpg.Connection | None = None
    start_ms = int(time.monotonic() * 1000)

    try:
        conn = await asyncpg.connect(config.DATABASE_URL)

        await conn.execute(
            "UPDATE ocr_documents SET ocr_status = 'PROCESSING', updated_at = NOW() WHERE job_id = $1",
            payload.job_id,
        )

        # Day4에서 실제 Clova OCR API 호출로 교체
        await asyncio.sleep(0.1)
        stub_text = f"[OCR stub] {payload.original_filename} 처리 완료"
        elapsed_ms = int(time.monotonic() * 1000) - start_ms

        await conn.execute(
            """
            INSERT INTO ocr_results (document_id, raw_text, processed_text, processing_time_ms)
            VALUES ($1, $2, $2, $3)
            """,
            payload.record_id,
            stub_text,
            elapsed_ms,
        )

        await conn.execute(
            "UPDATE ocr_documents SET ocr_status = 'DONE', updated_at = NOW() WHERE job_id = $1",
            payload.job_id,
        )

        # REQ-OCR-024 비고: 비동기 처리 Latency 수치 측정 필수 → ai_performance_metrics 기록
        await conn.execute(
            """
            INSERT INTO ai_performance_metrics (document_id, metric_type, metric_value, measured_at)
            VALUES ($1, 'LATENCY', $2, NOW())
            """,
            payload.record_id,
            float(elapsed_ms),
        )
        logger.info("OCR task done: job_id=%s elapsed_ms=%d", payload.job_id, elapsed_ms)

    except Exception as exc:
        logger.error("OCR task failed: job_id=%s error=%s", payload.job_id, exc)
        if conn is not None:
            try:
                await conn.execute(
                    "UPDATE ocr_documents SET ocr_status = 'FAILED', updated_at = NOW() WHERE job_id = $1",
                    payload.job_id,
                )
            except Exception:
                pass
    finally:
        if conn is not None:
            await conn.close()
