import asyncio
import base64
import json
import logging
import re
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
        doc_type = payload.doc_type_hint or await classify_document(ocr["raw_text"])
        elapsed_ms = int(time.monotonic() * 1000) - start_ms
        processed_text = _mask_pii(ocr["raw_text"])

        await conn.execute(
            """
            INSERT INTO ocr_results
                (document_id, raw_text, processed_text, clova_request_id, confidence_score, processing_time_ms, is_user_edited)
            VALUES ($1, $2, $3, $4, $5, $6, FALSE)
            """,
            payload.record_id,
            ocr["raw_text"],
            processed_text,
            ocr["request_id"],
            ocr["confidence"],
            elapsed_ms,
        )

        await conn.execute("DELETE FROM medications WHERE document_id = $1", payload.record_id)
        await conn.execute("DELETE FROM disease_codes WHERE document_id = $1", payload.record_id)
        if doc_type != "OTHER":
            parsed = await parse_medications_and_diseases(ocr["raw_text"], doc_type)
            medications = await _normalize_medication_names(conn, parsed["medications"])
            await _insert_medications(conn, payload.record_id, medications)
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
                error_msg = str(exc)[:500]
                updated = await conn.execute(
                    "UPDATE ocr_results SET error_message = $2 WHERE document_id = $1",
                    payload.record_id,
                    error_msg,
                )
                if updated == "UPDATE 0":
                    await conn.execute(
                        "INSERT INTO ocr_results (document_id, error_message, is_user_edited) VALUES ($1, $2, FALSE)",
                        payload.record_id,
                        error_msg,
                    )
            except Exception:
                pass
    finally:
        if conn is not None:
            await conn.close()


_PII_PATTERNS = [
    (re.compile(r"\d{6}-[1-8]\d{6}"), "******-*******"),  # 주민등록번호 + 외국인등록번호
    (re.compile(r"[A-Z]{1,2}\d{7,9}"), "***-*****"),  # 여권번호
    (re.compile(r"0\d{1,2}-\d{3,4}-\d{4}"), "***-****-****"),  # 전화번호
]


def _mask_pii(text: str) -> str:
    """processed_text의 주민번호·외국인등록번호·여권번호·전화번호를 마스킹합니다. (REQ-OCR-022)"""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


_DOSAGE_PATTERN = re.compile(
    r"\s*\(.*?\)\s*|\s*[0-9]+(?:\.[0-9]+)?\s*(?:mg|mL|g|밀리그람|밀리리터|마이크로그람|mcg|IU|%)\s*",
    re.IGNORECASE,
)


def _strip_dosage(name: str) -> str:
    return _DOSAGE_PATTERN.sub("", name).strip()


async def _normalize_medication_names(conn: asyncpg.Connection, medications: list[dict]) -> list[dict]:
    """OCR 약물명을 drug_master 테이블과 pg_trgm으로 매칭해 정규화합니다.
    word_similarity > 0.7이면 DB 약물명으로 교체, 미달이면 원문 유지.
    """
    result = []
    for m in medications:
        name = (m.get("medication_name") or "").strip()
        if not name:
            result.append(m)
            continue
        stripped = _strip_dosage(name)
        row = await conn.fetchrow(
            "SELECT item_name FROM drug_master WHERE word_similarity($1, item_name) > 0.7 ORDER BY word_similarity($1, item_name) DESC LIMIT 1",
            stripped,
        )
        if row:
            m = {**m, "medication_name": row["item_name"]}
        result.append(m)
    return result


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
