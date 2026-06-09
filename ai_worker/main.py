import asyncio
import json

import asyncpg
import redis.asyncio as aioredis

from ai_worker.core.config import config
from ai_worker.core.logger import setup_logger
from ai_worker.schemas.chat import ChatTaskPayload
from ai_worker.schemas.guide import GuideJobPayload
from ai_worker.schemas.ocr import OcrTaskPayload
from ai_worker.tasks.chat_task import process_chat
from ai_worker.tasks.guide_task import process_guide_task
from ai_worker.tasks.ocr_task import process_ocr

logger = setup_logger()


async def _recover_pending_jobs(redis_client: aioredis.Redis) -> None:
    """워커 시작 시 PENDING 상태로 남은 문서를 Redis에 재발행합니다."""
    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncpg.connect(config.DATABASE_URL)
        rows = await conn.fetch(
            """
            SELECT job_id, record_id, s3_key, s3_bucket, user_id, mime_type, original_filename
            FROM ocr_documents
            WHERE ocr_status = 'PENDING' AND is_active = TRUE
            """
        )
        if not rows:
            return
        for row in rows:
            payload = json.dumps(
                {
                    "job_id": str(row["job_id"]),
                    "record_id": row["record_id"],
                    "s3_key": row["s3_key"],
                    "s3_bucket": row["s3_bucket"],
                    "user_id": row["user_id"],
                    "mime_type": row["mime_type"],
                    "original_filename": row["original_filename"],
                }
            )
            await redis_client.publish(f"ocr:request:{row['job_id']}", payload)
            logger.info("Recovered pending job: job_id=%s record_id=%s", row["job_id"], row["record_id"])
        logger.info("Recovered %d pending job(s)", len(rows))
    except Exception as exc:
        logger.error("Failed to recover pending jobs: %s", exc)
    finally:
        if conn is not None:
            await conn.close()


async def main() -> None:
    redis_client: aioredis.Redis = aioredis.from_url(config.REDIS_URL, decode_responses=True)
    await _recover_pending_jobs(redis_client)

    pubsub = redis_client.pubsub()
    await pubsub.psubscribe("chat:request:*", "ocr:request:*", "guide:request:*")

    logger.info("AI Worker started — listening for chat/ocr/guide tasks")

    async for message in pubsub.listen():
        if message["type"] != "pmessage":
            continue

        channel: str = message.get("pattern", "") or ""
        raw: str = message["data"]

        try:
            data = json.loads(raw)
            if channel.startswith("chat:"):
                payload = ChatTaskPayload.model_validate(data)
                asyncio.create_task(process_chat(payload, redis_client))
            elif channel.startswith("ocr:"):
                payload = OcrTaskPayload.model_validate(data)
                asyncio.create_task(process_ocr(payload, redis_client))
            elif channel.startswith("guide:"):
                payload = GuideJobPayload.model_validate(data)
                logger.info("guide task dispatched job_id=%s", payload.job_id)
                asyncio.create_task(process_guide_task(payload))
            else:
                logger.warning("Unknown channel pattern: %s", channel)
        except Exception as exc:
            logger.error("Failed to dispatch task (channel=%s): %s", channel, exc)


if __name__ == "__main__":
    asyncio.run(main())
