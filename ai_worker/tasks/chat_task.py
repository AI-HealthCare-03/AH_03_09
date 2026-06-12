import redis.asyncio as aioredis

from ai_worker.core.llm import stream_chat
from ai_worker.schemas.chat import ChatTaskPayload


async def process_chat(payload: ChatTaskPayload, redis: aioredis.Redis) -> None:
    stream_channel = f"chat:stream:{payload.session_id}"
    history = [{"role": msg.role, "content": msg.content} for msg in payload.history]

    try:
        async for token in stream_chat(
            payload.user_message,
            history,
            payload.health_profile,
            payload.guides,
            payload.drug_details,
            payload.rag_results,
        ):
            await redis.publish(stream_channel, token)
        await redis.publish(stream_channel, "[DONE]")
    except Exception as exc:
        await redis.publish(stream_channel, f"[ERROR]{exc}")
