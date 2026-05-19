from openai import AsyncOpenAI

from ai_worker.core.config import settings
from ai_worker.schemas.chats import ChatTaskPayload, ChatTaskResult

SYSTEM_PROMPT = """당신은 AI 헬스케어 어시스턴트입니다.
사용자의 건강 관련 질문에 친절하고 정확하게 답변하세요.

다음 원칙을 반드시 지키세요:
- 의약품 복용 중단, 자가 진단, 처방 변경은 절대 권고하지 않습니다.
- 증상이 심각하거나 응급 상황으로 판단되면 즉시 119 또는 병원 방문을 안내합니다.
- 불확실한 정보는 "정확한 진단은 의료 전문가와 상담하시기 바랍니다"라고 명시합니다.
- 한국어로 답변합니다."""

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def generate_chat_response(payload: ChatTaskPayload) -> ChatTaskResult:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for item in payload.history[-20:]:
        role = "user" if item.role.upper() == "USER" else "assistant"
        messages.append({"role": role, "content": item.content})

    messages.append({"role": "user", "content": payload.user_message})

    response = await get_client().chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )

    answer = response.choices[0].message.content or "응답을 생성할 수 없습니다."
    return ChatTaskResult(task_id=payload.task_id, answer=answer)
