from enum import StrEnum

from openai import AsyncOpenAI

from ai_worker.core.config import config

_client: AsyncOpenAI | None = None


class ChatSkill(StrEnum):
    MEDICATION_GUIDE = "MEDICATION_GUIDE"
    DRUG_INTERACTION = "DRUG_INTERACTION"
    GENERAL = "GENERAL"


# 스킬별 시스템 프롬프트 템플릿 (Harness Engineering)
_SKILL_SYSTEM_PROMPTS: dict[ChatSkill, str] = {
    ChatSkill.DRUG_INTERACTION: """당신은 약물 상호작용 전문 AI 어시스턴트입니다.

역할: 약물 간 상호작용 분석 및 안전한 복용 가이드
- 언급된 약물 조합의 알려진 상호작용을 설명합니다.
- 위험 수준(주의/경고/금기)을 명확히 구분합니다.
- 불확실한 경우 반드시 약사·의사 확인을 권장합니다.

답변 형식: 1) 상호작용 여부 → 2) 위험 수준 → 3) 권장 행동""",
    ChatSkill.MEDICATION_GUIDE: """당신은 복약 지도 전문 AI 어시스턴트입니다.

역할: 올바른 복약 방법과 주의사항 안내
- 복용 시간, 용량, 복용 방법(식전/식후/공복 등)을 명확히 설명합니다.
- 보관 방법, 놓친 복용 시 대처법을 안내합니다.
- 처방전·약봉투 내용을 쉬운 언어로 해석해 드립니다.

답변 형식: 1) 복용 방법 → 2) 주의사항 → 3) 보관/기타""",
    ChatSkill.GENERAL: """당신은 복약 관리 전문 AI 어시스턴트입니다.

역할:
- 약봉투·처방전 기반 복약 안내 (복용법, 복용 시간, 주의사항)
- 약물 부작용·상호작용 정보 제공
- 약 관련 궁금증 상담 (약국 이용, 약품 보관법 등)

답변 원칙:
- 모든 답변은 한국어로, 친근하고 이해하기 쉽게 작성합니다.
- 핵심 정보를 먼저 전달하고 세부 내용을 이어서 설명합니다.
- 의학적 진단이나 처방은 제공할 수 없으며, 심각한 증상에는 즉시 전문의 상담을 권합니다.
- 불확실한 정보는 반드시 명시하고, 필요시 의사·약사 확인을 권장합니다.""",
}

# 스킬별 키워드
_SKILL_KEYWORDS: dict[ChatSkill, list[str]] = {
    ChatSkill.DRUG_INTERACTION: [
        "같이 먹어",
        "함께 먹어",
        "함께 복용",
        "같이 복용",
        "동시에 복용",
        "상호작용",
        "섞어도",
        "병용",
        "같이 마셔",
        "혼용",
    ],
    ChatSkill.MEDICATION_GUIDE: [
        "복용법",
        "복용 방법",
        "어떻게 먹",
        "언제 먹",
        "몇 번 먹",
        "몇 알",
        "식전",
        "식후",
        "공복",
        "보관",
        "유통기한",
        "얼마나 먹",
        "복약",
        "처방전",
        "약봉투",
        "용량",
        "놓쳤",
        "빠뜨렸",
    ],
}

_EXERCISE_LABEL = {"REGULAR": "규칙적 (주 3회 이상)", "IRREGULAR": "비규칙적", "NONE": ""}
_ALCOHOL_LABEL = {"NONE": "", "MODERATE": "가끔 (주 1~2회)", "HEAVY": "자주 (주 3회 이상)"}

_SUMMARY_THRESHOLD = 12
_RECENT_KEEP = 8


def detect_skill(user_message: str) -> ChatSkill:
    """키워드 기반으로 사용자 메시지 의도를 분류해 적절한 스킬을 반환한다."""
    for skill in (ChatSkill.DRUG_INTERACTION, ChatSkill.MEDICATION_GUIDE):
        for keyword in _SKILL_KEYWORDS[skill]:
            if keyword in user_message:
                return skill
    return ChatSkill.GENERAL


def _build_system_prompt(health_profile: dict | None, skill: ChatSkill = ChatSkill.GENERAL) -> str:
    base = _SKILL_SYSTEM_PROMPTS[skill]

    if not health_profile:
        return base

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
        return base

    profile_section = "\n\n[사용자 건강 프로필 — 답변 시 반드시 반영하세요]\n" + "\n".join(lines)
    return base + profile_section


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


async def _compress_history(old_messages: list[dict], client: AsyncOpenAI) -> str:
    """오래된 대화를 짧게 요약해 컨텍스트로 유지한다."""
    text = "\n".join(f"{'사용자' if m['role'] == 'user' else 'AI'}: {m['content']}" for m in old_messages)
    resp = await client.chat.completions.create(
        model=config.OPENAI_CHAT_MODEL,
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
    skill = detect_skill(user_message)
    system_prompt = _build_system_prompt(health_profile, skill)
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
        model=config.OPENAI_CHAT_MODEL,
        messages=messages,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
