from openai import AsyncOpenAI

from ai_worker.core.config import config

_client: AsyncOpenAI | None = None

_BASE_SYSTEM_PROMPT = """당신은 복약 관리 전문 AI 어시스턴트입니다.

역할:
- 약봉투·처방전 기반 복약 안내 (복용법, 복용 시간, 주의사항)
- 약물 부작용·상호작용 정보 제공
- 약 관련 궁금증 상담 (약국 이용, 약품 보관법 등)

답변 원칙:
- 모든 답변은 한국어로, 친근하고 이해하기 쉽게 작성합니다.
- 핵심 정보를 먼저 전달하고 세부 내용을 이어서 설명합니다.
- 의학적 진단이나 처방은 제공할 수 없으며, 심각한 증상에는 즉시 전문의 상담을 권합니다.
- 불확실한 정보는 반드시 명시하고, 필요시 의사·약사 확인을 권장합니다."""

_EXERCISE_LABEL = {"REGULAR": "규칙적 (주 3회 이상)", "IRREGULAR": "비규칙적", "NONE": ""}
_ALCOHOL_LABEL = {"NONE": "", "MODERATE": "가끔 (주 1~2회)", "HEAVY": "자주 (주 3회 이상)"}


def _build_system_prompt(health_profile: dict | None) -> str:
    if not health_profile:
        return _BASE_SYSTEM_PROMPT

    lines: list[str] = []

    conditions = health_profile.get("primary_conditions") or []
    if conditions:
        lines.append(f"- 기저질환: {', '.join(conditions)}")

    allergies = health_profile.get("allergies") or []
    if allergies:
        lines.append(f"- 알레르기: {', '.join(allergies)}")

    meds = health_profile.get("current_medications") or []
    if meds:
        lines.append(f"- 복용 중인 약물: {', '.join(meds)}")

    lifestyle: list[str] = []
    exercise = _EXERCISE_LABEL.get(health_profile.get("lifestyle_exercise", "NONE"), "")
    if exercise:
        lifestyle.append(f"운동 {exercise}")
    if health_profile.get("lifestyle_smoking"):
        lifestyle.append("흡연")
    alcohol = _ALCOHOL_LABEL.get(health_profile.get("lifestyle_alcohol", "NONE"), "")
    if alcohol:
        lifestyle.append(f"음주 {alcohol}")
    if lifestyle:
        lines.append(f"- 생활습관: {', '.join(lifestyle)}")

    if not lines:
        return _BASE_SYSTEM_PROMPT

    profile_section = "\n\n[사용자 건강 프로필 — 답변 시 반드시 반영하세요]\n" + "\n".join(lines)
    return _BASE_SYSTEM_PROMPT + profile_section


_SUMMARY_THRESHOLD = 12  # 이 수 초과 시 오래된 메시지 요약
_RECENT_KEEP = 8  # 항상 원문으로 유지할 최근 메시지 수


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


async def _compress_history(old_messages: list[dict], client: AsyncOpenAI) -> str:
    """오래된 대화를 짧게 요약해 컨텍스트로 유지한다."""
    text = "\n".join(f"{'사용자' if m['role'] == 'user' else 'AI'}: {m['content']}" for m in old_messages)
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "아래 대화를 3~5문장으로 핵심만 요약하세요. "
                    "사용자가 물어본 약물명, 중요한 복약 정보, 주요 결론을 포함하세요."
                ),
            },
            {"role": "user", "content": text},
        ],
        max_tokens=250,
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""


async def stream_chat(user_message: str, history: list[dict], health_profile: dict | None = None):
    system_prompt = _build_system_prompt(health_profile)
    client = get_openai_client()

    if len(history) > _SUMMARY_THRESHOLD:
        cutoff = len(history) - _RECENT_KEEP
        summary = await _compress_history(history[:cutoff], client)
        system_prompt += f"\n\n[이전 대화 요약 — 이 내용을 기억하고 답변에 활용하세요]\n{summary}"
        trimmed_history = history[cutoff:]
    else:
        trimmed_history = history

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(trimmed_history)
    messages.append({"role": "user", "content": user_message})

    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
