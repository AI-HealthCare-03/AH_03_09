import base64
import json
import logging
import time
import uuid as uuid_lib

import asyncpg
import httpx
import redis.asyncio as aioredis

from ai_worker.core.config import config
from ai_worker.schemas.ocr import OcrTaskPayload
from ai_worker.tasks.doc_classifier import classify_document
from ai_worker.tasks.ocr_parser import parse_medications_and_diseases

logger = logging.getLogger(__name__)

_LOCAL_BUCKET = "__local__"

_MIME_TO_FORMAT = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "application/pdf": "pdf",
}


async def _read_file(s3_key: str, s3_bucket: str) -> bytes:
    """로컬 스토리지 또는 S3에서 파일을 읽어 반환합니다."""
    if s3_bucket == _LOCAL_BUCKET:
        with open(s3_key, "rb") as f:
            return f.read()

    import boto3

    def _get() -> bytes:
        s3 = boto3.client("s3")
        obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
        return obj["Body"].read()

    import asyncio

    return await asyncio.to_thread(_get)


async def _call_clova_ocr(content: bytes, mime_type: str) -> dict:
    """Clova OCR API를 호출하고 파싱된 결과를 반환합니다.

    Returns:
        {"raw_text": str, "confidence": float, "request_id": str}
    """
    fmt = _MIME_TO_FORMAT.get(mime_type, "jpeg")
    payload = {
        "version": "V2",
        "requestId": str(uuid_lib.uuid4()),
        "timestamp": 0,
        "images": [
            {
                "format": fmt,
                "name": "ocr_image",
                "data": base64.b64encode(content).decode(),
            }
        ],
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            config.CLOVA_OCR_INVOKE_URL,
            headers={
                "X-OCR-SECRET": config.CLOVA_OCR_SECRET_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code != 200:
        raise RuntimeError(f"Clova OCR API 오류: {resp.status_code} {resp.text[:200]}")

    result = resp.json()
    images = result.get("images", [])
    if not images or images[0].get("inferResult") != "SUCCESS":
        msg = images[0].get("message", "unknown") if images else "no images"
        raise RuntimeError(f"Clova OCR 인식 실패: {msg}")

    fields = images[0].get("fields", [])

    # lineBreak 기준으로 줄 구성
    lines: list[str] = []
    current: list[str] = []
    for field in fields:
        current.append(field.get("inferText", ""))
        if field.get("lineBreak", False):
            lines.append(" ".join(current))
            current = []
    if current:
        lines.append(" ".join(current))

    raw_text = "\n".join(lines)
    confidences = [f.get("inferConfidence", 0.0) for f in fields]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return {
        "raw_text": raw_text,
        "confidence": round(avg_confidence, 4),
        "request_id": result.get("requestId", ""),
    }


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

        content = await _read_file(payload.s3_key, payload.s3_bucket)
        ocr = await _call_clova_ocr(content, payload.mime_type)
        doc_type = await classify_document(ocr["raw_text"])
        elapsed_ms = int(time.monotonic() * 1000) - start_ms

        await conn.execute(
            """
            INSERT INTO ocr_results
                (document_id, raw_text, processed_text, clova_request_id, confidence_score, processing_time_ms, is_user_edited)
            VALUES ($1, $2, $2, $3, $4, $5, FALSE)
            """,
            payload.record_id,
            ocr["raw_text"],
            ocr["request_id"],
            ocr["confidence"],
            elapsed_ms,
        )

        parsed = await parse_medications_and_diseases(ocr["raw_text"], doc_type)
        await _insert_medications(conn, payload.record_id, parsed["medications"])
        if doc_type == "PRESCRIPTION":
            await _insert_disease_codes(conn, payload.record_id, parsed["disease_codes"])

        await conn.execute(
            "UPDATE ocr_documents SET ocr_status = 'DONE', doc_type = $2, updated_at = NOW() WHERE job_id = $1",
            payload.job_id,
            doc_type,
        )

        # REQ-OCR-024 비고: Latency 수치 측정 필수
        await conn.execute(
            """
            INSERT INTO ai_performance_metrics (document_id, metric_type, metric_value, measured_at)
            VALUES ($1, 'LATENCY', $2, NOW())
            """,
            payload.record_id,
            float(elapsed_ms),
        )

        logger.info(
            "OCR task done: job_id=%s elapsed_ms=%d confidence=%.4f doc_type=%s",
            payload.job_id,
            elapsed_ms,
            ocr["confidence"],
            doc_type,
        )

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


async def _insert_medications(conn: asyncpg.Connection, record_id: int, medications: list[dict]) -> None:
    for m in medications:
        await conn.execute(
            """
            INSERT INTO medications
                (document_id, medication_name, edi_code, generic_name, dosage, frequency, timing,
                 usage_time, duration_days, time_of_day, warnings, confidence_score,
                 is_confirmed, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, FALSE, TRUE)
            """,
            record_id,
            m.get("medication_name") or "",
            m.get("edi_code"),
            m.get("generic_name"),
            m.get("dosage"),
            m.get("frequency"),
            m.get("timing"),
            m.get("usage_time"),
            m.get("duration_days"),
            json.dumps(m["time_of_day"], ensure_ascii=False) if m.get("time_of_day") is not None else None,
            json.dumps(m["warnings"], ensure_ascii=False) if m.get("warnings") is not None else None,
            m.get("confidence_score"),
        )


async def _insert_disease_codes(conn: asyncpg.Connection, record_id: int, disease_codes: list[dict]) -> None:
    for c in disease_codes:
        await conn.execute(
            """
            INSERT INTO disease_codes
                (document_id, icd10_code, disease_name, confidence_score,
                 is_confirmed, is_active)
            VALUES ($1, $2, $3, $4, FALSE, TRUE)
            """,
            record_id,
            c.get("icd10_code") or "",
            c.get("disease_name"),
            c.get("confidence_score"),
        )
