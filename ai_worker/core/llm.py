from openai import AsyncOpenAI

from ai_worker.core.config import config

_client: AsyncOpenAI | None = None

HEALTH_SYSTEM_PROMPT = """당신은 친절하고 전문적인 건강 상담 챗봇입니다.
- 건강, 영양, 운동, 의약품에 관한 질문에 성실히 답변합니다.
- 의학적 진단은 제공할 수 없으며, 심각한 증상은 반드시 전문의 상담을 권유합니다.
- 모든 답변은 한국어로 합니다.
- 과학적 근거가 있는 정보를 바탕으로 답변하며, 불확실한 내용은 그렇다고 명시합니다."""


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


async def stream_chat(user_message: str, history: list[dict]):
    messages = [{"role": "system", "content": HEALTH_SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    client = get_openai_client()
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
