from openai import AsyncOpenAI

from ai_worker.core.config import settings
from ai_worker.schemas.chats import ChatTaskPayload, ChatTaskResult

BASE_SYSTEM_PROMPT = """당신은 AI 헬스케어 어시스턴트입니다.
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


def _build_system_prompt(payload: ChatTaskPayload) -> str:
    if payload.health_profile is None:
        return BASE_SYSTEM_PROMPT

    hp = payload.health_profile
    smoking_text = "흡연" if hp.lifestyle_smoking else ("비흡연" if hp.lifestyle_smoking is False else "정보 없음")

    profile_lines = [
        "\n\n[사용자 건강 프로필]",
        f"- 진단명: {', '.join(hp.primary_conditions) if hp.primary_conditions else '없음'}",
        f"- 알레르기: {', '.join(hp.allergies) if hp.allergies else '없음'}",
        f"- 복용 중인 약물: {', '.join(hp.current_medications) if hp.current_medications else '없음'}",
        f"- 운동 습관: {hp.lifestyle_exercise or '정보 없음'}",
        f"- 흡연: {smoking_text}",
        f"- 음주: {hp.lifestyle_alcohol or '정보 없음'}",
        "\n위 정보를 바탕으로 사용자에게 맞춤형 건강 안내를 제공하세요.",
    ]
    return BASE_SYSTEM_PROMPT + "\n".join(profile_lines)


async def _generate_title(user_message: str) -> str:
    response = await get_client().chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "사용자의 첫 질문을 보고 채팅 세션 제목을 15자 이내 한국어로 생성하세요. 제목만 출력하고 다른 내용은 쓰지 마세요.",
            },
            {"role": "user", "content": user_message},
        ],
        max_tokens=30,
        temperature=0.3,
    )
    return (response.choices[0].message.content or "새 채팅").strip()


async def generate_chat_response(payload: ChatTaskPayload) -> ChatTaskResult:
    system_prompt = _build_system_prompt(payload)
    messages = [{"role": "system", "content": system_prompt}]

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
    title = await _generate_title(payload.user_message) if not payload.history else None
    return ChatTaskResult(task_id=payload.task_id, answer=answer, title=title)
