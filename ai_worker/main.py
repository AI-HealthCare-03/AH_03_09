import asyncio
import json

import redis.asyncio as aioredis

from ai_worker.core.config import settings
from ai_worker.core.logger import logger
from ai_worker.schemas.chats import ChatTaskPayload
from ai_worker.tasks.chat_task import generate_chat_response

AI_TASK_QUEUE = "ai:chat:queue"
AI_RESULT_PREFIX = "ai:chat:result:"
AI_RESULT_TTL = 300


async def run_worker(redis: aioredis.Redis) -> None:
    logger.info("AI Chat Worker started.")
    while True:
        try:
            raw = await redis.blpop(AI_TASK_QUEUE, timeout=0)
            if raw is None:
                continue

            _, payload_json = raw
            payload = ChatTaskPayload.model_validate_json(payload_json)
            logger.info(f"Task received: {payload.task_id}")

            result = await generate_chat_response(payload)

            result_key = f"{AI_RESULT_PREFIX}{result.task_id}"
            await redis.lpush(result_key, result.model_dump_json())
            await redis.expire(result_key, AI_RESULT_TTL)

            logger.info(f"Task completed: {result.task_id}")

        except Exception as e:
            logger.error(f"Worker error: {e}")


async def main() -> None:
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await run_worker(redis)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
