import asyncio
import json

import redis.asyncio as aioredis

from ai_worker.core.config import config
from ai_worker.core.logger import setup_logger
from ai_worker.schemas.chat import ChatTaskPayload
from ai_worker.tasks.chat_task import process_chat

logger = setup_logger()


async def main() -> None:
    redis_client: aioredis.Redis = aioredis.from_url(config.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe("chat:request:*")

    logger.info("AI Worker started — listening for chat tasks")

    async for message in pubsub.listen():
        if message["type"] != "pmessage":
            continue
        try:
            data = message["data"]
            payload = ChatTaskPayload.model_validate(json.loads(data))
            asyncio.create_task(process_chat(payload, redis_client))
        except Exception as exc:
            logger.error(f"Failed to dispatch task: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
