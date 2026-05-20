import asyncio
import json

import redis.asyncio as aioredis

from ai_worker.core.config import config
from ai_worker.core.logger import setup_logger
from ai_worker.schemas.chat import ChatTaskPayload
from ai_worker.schemas.ocr import OcrTaskPayload
from ai_worker.tasks.chat_task import process_chat
from ai_worker.tasks.ocr_task import process_ocr

logger = setup_logger()


async def main() -> None:
    redis_client: aioredis.Redis = aioredis.from_url(config.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe("chat:request:*", "ocr:request:*")

    logger.info("AI Worker started — listening for chat/ocr tasks")

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
            else:
                logger.warning("Unknown channel pattern: %s", channel)
        except Exception as exc:
            logger.error("Failed to dispatch task (channel=%s): %s", channel, exc)


if __name__ == "__main__":
    asyncio.run(main())
