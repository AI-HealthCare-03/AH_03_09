import json
from enum import StrEnum

from openai import AsyncOpenAI

from ai_worker.core.config import config

_client: AsyncOpenAI | None = None


class ChatSkill(StrEnum):
    MEDICATION_GUIDE = "MEDICATION_GUIDE"
    DRUG_INTERACTION = "DRUG_INTERACTION"
    SIDE_EFFECT = "SIDE_EFFECT"
    EMERGENCY = "EMERGENCY"
    DISEASE_INQUIRY = "DISEASE_INQUIRY"
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
    ChatSkill.SIDE_EFFECT: """당신은 약물 부작용 상담 전문 AI 어시스턴트입니다.

역할: 약물 복용 후 나타날 수 있는 부작용 안내 및 대처법 제공
- 증상이 해당 약물의 알려진 부작용인지 설명합니다.
- 경미한 부작용과 즉시 병원 방문이 필요한 심각한 부작용을 구분합니다.
- 부작용 발생 시 복약 중단 여부를 임의로 결정하지 말고 의사·약사와 상의하도록 안내합니다.

답변 형식: 1) 증상과 해당 약물 연관성 → 2) 심각도 판단 → 3) 권장 행동""",
    ChatSkill.EMERGENCY: """당신은 응급 증상 판단 전문 AI 어시스턴트입니다.

역할: 약물 복용 후 나타난 응급 증상 여부 판단 및 즉각적인 행동 안내
- 증상의 긴급도를 신속하게 판단합니다.
- 즉시 119 신고 또는 응급실 방문이 필요한 경우 명확하게 안내합니다.
- 과다복용, 알레르기 반응(아나필락시스), 호흡 곤란 등 위험 상황에 최우선으로 대응합니다.
- AI 판단에 의존하지 말고 반드시 전문 의료진의 도움을 받도록 강조합니다.

답변 형식: 1) 긴급도 판단 (즉시/주의/경과 관찰) → 2) 즉각 행동 지시 → 3) 주의사항""",
    ChatSkill.DISEASE_INQUIRY: """당신은 복약 관리 전문 AI 어시스턴트입니다.

사용자가 자신의 질병·건강 상태에 대해 질문했습니다.
반드시 아래 형식으로만 답변하세요. 두 출처를 절대 한 문장에 합치지 마세요.

[답변 구조 — 해당하는 항목만 포함]

① 사용자가 직접 입력한 건강정보가 있을 경우:
   "귀하께서 직접 입력하신 건강정보에는 [내용]이 포함되어 있습니다."
   → 이 항목은 사용자 본인이 입력한 정보임을 반드시 명시합니다.

② 처방전에서 인식된 질병코드가 있을 경우:
   - 질병코드 번호(예: M75.3)는 기본적으로 표시하지 않습니다.
   - 질병명들을 신체 부위나 계통별로 묶어 자연스러운 한국어로 짧게 요약합니다.
     예: "처방전에서 어깨·관절 관련 질환과 위장 관련 질환 정보가 확인됐어요."
   - 사용자가 코드 번호를 명시적으로 요청할 경우에만 코드를 알려줍니다.
   - 요약 후 짧게 한 줄: "정확한 진단은 담당 의사 선생님께 꼭 확인해 주세요."

③ 질병코드 없이 약물 정보만 있는 경우 (약봉투 등):
   - 아래 형식으로만 답변하세요:
     "올려주신 문서에는 질병코드 정보가 포함되어 있지 않아 정확한 병명은 확인하기 어렵습니다.
      처방전을 올리시면 질병코드를 바탕으로 병명 정보를 안내드릴 수 있어요.
      대신 처방된 약의 복약 방법, 복용 시간, 주의사항 등을 안내해드릴 수 있습니다. 궁금한 점을 물어보세요!"
   - 약물 용도를 근거로 병명을 추정하거나 나열하지 마세요.

절대 금지:
- 두 출처(건강 프로필 + 처방전 코드)를 한 문장으로 합쳐서 설명
- 사용자가 요청하지 않았는데 코드 번호(M75.3 등)를 먼저 나열하기""",
    ChatSkill.GENERAL: """당신은 복약 관리 전문 AI 어시스턴트입니다.

역할:
- 약봉투·처방전 기반 복약 안내 (복용법, 복용 시간, 주의사항)
- 약물 부작용·상호작용 정보 제공
- 약 관련 궁금증 상담 (약국 이용, 약품 보관법 등)

답변 원칙:
- 모든 답변은 한국어로, 친근하고 이해하기 쉽게 작성합니다.
- 핵심 정보를 먼저 전달하고 세부 내용을 이어서 설명합니다.
- 의학적 진단이나 처방은 제공할 수 없으며, 심각한 증상에는 즉시 전문의 상담을 권합니다.
- 불확실한 정보는 반드시 명시하고, 필요시 의사·약사 확인을 권장합니다.

질병 정보 답변 규칙:
- 건강 프로필 질환 정보 → "귀하께서 입력하신 건강정보에는 [질환명] 정보가 포함되어 있습니다."로 출처 명시.
- 처방전 질병코드 → 코드 번호는 표시하지 않고, 질병명을 신체 부위·계통별로 묶어 자연스럽게 요약합니다. 사용자가 코드 번호를 명시적으로 요청할 경우에만 알려줍니다.
- 처방전 코드 요약 후 "정확한 진단은 담당 의사 선생님께 꼭 확인해 주세요."를 짧게 추가합니다.
- 약물명만으로 "이 약이 처방되었으니 귀하는 X 질환입니다"처럼 특정 질환을 단정 추정하지 않습니다.
- "귀하의 질병은 X입니다" / "당신이 가지고 있는 질병은 X입니다" 형태의 확정 진단 표현은 절대 사용하지 않습니다.""",
}

# TODO: 식약처 공식 약품명 매핑 — ILIKE 퍼지 매칭 대신 EDI 코드 기반 표준 약품명으로 스킬 정확도 향상
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
    ChatSkill.SIDE_EFFECT: [
        "부작용",
        "이상반응",
        "두통",
        "어지러워",
        "어지럽",
        "구역",
        "구토",
        "두드러기",
        "가려워",
        "졸려",
        "졸음",
        "속 쓰려",
        "복통",
        "설사",
        "먹고 나서",
        "복용 후",
    ],
    ChatSkill.DISEASE_INQUIRY: [
        "내 질병",
        "무슨 병",
        "어떤 병",
        "내 병",
        "질환이 뭐",
        "어디 아파",
        "무슨 질환",
        "내 건강 상태",
        "어떤 질환",
        "병명이 뭐",
        "질병이 뭐",
        "무슨 병을 앓",
        "진단명",
        "내 진단",
    ],
    ChatSkill.EMERGENCY: [
        "호흡 곤란",
        "숨 못 쉬",
        "숨쉬기",
        "심한 두근",
        "가슴 통증",
        "쓰러질 것",
        "쓰러졌",
        "의식",
        "경련",
        "발작",
        "혈압",
        "쇼크",
        "응급",
        "119",
        "많이 먹었",
        "과다",
    ],
}

_EXERCISE_LABEL = {"REGULAR": "규칙적 (주 3회 이상)", "IRREGULAR": "비규칙적", "NONE": ""}
_ALCOHOL_LABEL = {"NONE": "", "MODERATE": "가끔 (주 1~2회)", "HEAVY": "자주 (주 3회 이상)"}

_SUMMARY_THRESHOLD = 12
_DRUG_FIELD_MAX = 500  # 식약처 텍스트가 길어 프롬프트 토큰 절약
_RECENT_KEEP = 8
_MEDICAL_DISCLAIMERS: dict[ChatSkill, str] = {
    ChatSkill.MEDICATION_GUIDE: "\n\n⚠️ 본 답변은 AI가 생성한 의료 정보입니다. 정확한 복약 지도는 담당 의사·약사에게 확인하시기 바랍니다.",
    ChatSkill.DRUG_INTERACTION: "\n\n⚠️ 본 답변은 AI가 생성한 의료 정보입니다. 약물 상호작용에 대한 정확한 확인은 담당 의사·약사와 상담하시기 바랍니다.",
    ChatSkill.SIDE_EFFECT: "\n\n⚠️ 본 답변은 AI가 생성한 의료 정보입니다. 부작용이 지속되거나 심각한 경우 즉시 의사·약사와 상담하시기 바랍니다.",
    ChatSkill.EMERGENCY: "\n\n🚨 응급 상황이라면 즉시 119에 신고하세요. 본 AI 답변에만 의존하지 마시기 바랍니다.",
    ChatSkill.DISEASE_INQUIRY: "\n\n⚠️ 본 답변은 AI가 생성한 의료 정보입니다. 정확한 진단 및 치료는 반드시 담당 의사와 상담하시기 바랍니다.",
    ChatSkill.GENERAL: "\n\n⚠️ 본 답변은 AI가 생성한 의료 정보입니다. 정확한 진단 및 치료는 담당 의사와 상담하시기 바랍니다.",
}


def _strip_disclaimers(content: str) -> str:
    for d in _MEDICAL_DISCLAIMERS.values():
        content = content.replace(d, "")
    return content.rstrip()


def detect_skill(user_message: str) -> ChatSkill:
    """키워드 기반으로 사용자 메시지 의도를 분류해 적절한 스킬을 반환한다."""
    for skill in (
        ChatSkill.EMERGENCY,
        ChatSkill.DRUG_INTERACTION,
        ChatSkill.SIDE_EFFECT,
        ChatSkill.MEDICATION_GUIDE,
        ChatSkill.DISEASE_INQUIRY,
    ):
        for keyword in _SKILL_KEYWORDS[skill]:
            if keyword in user_message:
                return skill
    return ChatSkill.GENERAL


def _build_single_guide_block(guide: dict) -> str:
    """가이드 1개의 내용을 텍스트 블록으로 변환한다."""
    lines: list[str] = []

    medications = guide.get("medications") or []
    if medications:
        lines.append(f"- 처방 약물: {', '.join(medications)}")

    schedule = guide.get("schedule") or []
    if schedule:
        schedule_lines = [f"  · {s.get('time', '')}: {', '.join(s.get('medications', []))}" for s in schedule]
        lines.append("- 복약 스케줄:\n" + "\n".join(schedule_lines))

    instructions = guide.get("key_instructions") or []
    if instructions:
        instruction_lines = [f"  · {i}" for i in instructions]
        lines.append("- 주요 지시사항:\n" + "\n".join(instruction_lines))

    disease_codes = guide.get("disease_codes") or []
    disease_names = guide.get("disease_names") or []
    if disease_codes:
        pairs = [f"{c}({n})" if n else c for c, n in zip(disease_codes, disease_names, strict=False)]
        lines.append(f"- 질병코드(참고용, 확정 진단 아님): {', '.join(pairs)}")
    elif guide.get("medications"):
        lines.append("- 질병코드: 없음 (약봉투 등 — 병명 확인 불가, 복약 가이드 안내만 가능)")

    return "\n".join(lines)


def _build_guides_section(guides: list[dict]) -> str:
    """가이드 목록을 시스템 프롬프트 섹션으로 변환한다.

    가이드가 1개면 바로 내용 포함, 2개 이상이면 레이블 붙여 나열하고
    처방·질병 관련 질문 시 어느 가이드를 기준으로 할지 먼저 물어보도록 지시한다.
    """
    non_empty = [g for g in guides if g.get("medications") or g.get("disease_codes")]
    if not non_empty:
        return ""

    if len(non_empty) == 1:
        g = non_empty[0]
        label = g.get("label", "가이드 1")
        date = g.get("created_at", "")
        header = f"\n\n[처방 가이드 — {label}" + (f" ({date})" if date else "") + "]"
        header += "\n※ 아래 데이터는 OCR로 인식된 내용이므로 약품명·용어에 오탈자가 있을 수 있습니다. 데이터를 해석할 때만 참고하고, 당신의 답변 문장 자체는 원래대로 자연스럽게 작성하세요."
        block = _build_single_guide_block(g)
        return header + "\n" + block if block else ""

    # 여러 가이드
    lines = [
        "\n\n[처방 가이드 목록 — 사용자가 업로드한 처방전·복약정보]",
        "※ 아래 데이터는 OCR로 인식된 내용이므로 약품명·용어에 오탈자가 있을 수 있습니다. 데이터를 해석할 때만 참고하고, 당신의 답변 문장 자체는 원래대로 자연스럽게 작성하세요.",
        "",
        "⚑ 처방 내용·질병 관련 질문이 들어오면, 답변하기 전에 반드시 아래 중 어느 가이드를 기준으로 할지 사용자에게 먼저 물어보세요.",
        "  단, 사용자가 이미 가이드를 지정했거나 대화 문맥에서 특정 가이드가 명확하다면 바로 답변하세요.",
        "  처방·질병과 무관한 일반 복약 질문(예: '이 약은 언제 먹나요?')은 물어보지 않아도 됩니다.",
        "",
    ]
    for g in non_empty:
        label = g.get("label", "")
        date = g.get("created_at", "")
        disease_names = g.get("disease_names") or []
        disease_codes = g.get("disease_codes") or []
        # 병명 우선, 없으면 질병코드 fallback
        summary_items = disease_names if disease_names else disease_codes
        summary = ", ".join(summary_items[:2]) + ("…" if len(summary_items) > 2 else "")
        header = f"■ {label}" + (f" ({date})" if date else "") + (f" — {summary}" if summary else "")
        lines.append(header)
        block = _build_single_guide_block(g)
        if block:
            lines.append(block)
        lines.append("")

    return "\n".join(lines)


def _build_user_info(health_profile: dict) -> list[str]:
    lines: list[str] = []
    gender = health_profile.get("gender")
    age_range = health_profile.get("age_range")
    birthyear = health_profile.get("birthyear")
    user_info: list[str] = []
    if gender:
        if gender in ("M", "male"):
            user_info.append("남성")
        elif gender in ("F", "female"):
            user_info.append("여성")
    if age_range:
        user_info.append(f"{age_range}대")
    elif birthyear:
        user_info.append(f"{birthyear}년생")
    if user_info:
        lines.append(f"- 기본정보: {', '.join(user_info)}")
    height = health_profile.get("height_cm")
    weight = health_profile.get("weight_kg")
    if height or weight:
        parts = [*([f"키 {height}cm"] if height else []), *([f"몸무게 {weight}kg"] if weight else [])]
        lines.append(f"- 신체정보: {', '.join(parts)}")
    return lines


def _build_profile_section(health_profile: dict) -> str:
    lines: list[str] = _build_user_info(health_profile)

    bp_sys = health_profile.get("blood_pressure_systolic")
    bp_dia = health_profile.get("blood_pressure_diastolic")
    if bp_sys and bp_dia:
        lines.append(f"- 혈압: {bp_sys}/{bp_dia} mmHg")

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
        return ""
    return (
        "\n\n[사용자가 직접 입력한 건강정보 — 질병·건강 상태 관련 답변 시 반드시 이 내용을 언급하고, 출처를 '귀하께서 입력하신 건강정보에는 ...'으로 명시하세요]\n"
        + "\n".join(lines)
    )


_SOURCE_RULES = """

[서비스 범위 규칙 — 최우선 적용]
이 AI는 약·건강·복약 관련 모든 질문에 답변합니다.
약, 의약품, 복약, 처방전, 약봉투, 건강, 증상, 질병, 응급 상황 등과 조금이라도 관련된 질문이면 반드시 정상 답변하세요.

단, 약·건강과 전혀 무관한 주제(날씨, 주식, 음식 레시피, 스포츠, 정치, 여행 등)에 대한 질문에만:
→ "저는 처방전·약봉투 기반 복약 관리를 위한 AI입니다. 약 복용법, 처방 내용, 부작용 등 약과 관련된 질문을 해주세요." 라고만 답하고 즉시 멈추세요.
→ 어떠한 추가 설명, 안내, 공감 표현도 덧붙이지 마세요.

[출처 구분 및 진단 표현 규칙 — 건강 정보가 포함된 모든 답변에 반드시 적용]

■ 건강 프로필(사용자 직접 입력) 정보가 있을 때:
   반드시 → "귀하께서 입력하신 건강정보에는 [질환명/건강수치] 정보가 포함되어 있습니다."
   (예: "귀하께서 입력하신 건강정보에는 고혈압 정보가 포함되어 있습니다.")

■ 처방전/복약정보(OCR 인식) 질병코드가 있을 때:
   - 질병코드 번호(예: M75.3)는 기본적으로 표시하지 않습니다.
   - 질병명을 신체 부위·계통별로 묶어 자연스러운 한국어로 요약합니다.
   - 사용자가 코드 번호를 명시적으로 요청할 경우에만 알려줍니다.
   - 요약 후 짧게: "정확한 진단은 담당 의사 선생님께 꼭 확인해 주세요."

■ 두 정보가 모두 있을 때: 건강 프로필 안내를 먼저, 처방전 질병 요약을 두 번째로 반드시 모두 포함합니다.

절대 금지 표현:
- "귀하의 질병은 X입니다" / "당신이 가지고 있는 질병은 X입니다" 등 확정 진단 형태
- "당신이 언급한/말씀하신 질병코드" → 질병코드는 사용자가 직접 언급한 것이 아니라 의료문서에서 인식된 것
- 약물명만으로 "이 약은 X 질환에 처방되므로 귀하는 X 질환입니다" 형태의 단정 추정
- 출처를 구분하지 않고 모든 정보를 하나의 확정된 사실처럼 제시하는 표현

[면책 문구 규칙]
답변 본문 어디에도 ⚠️ 또는 🚨 이모티콘을 직접 사용하지 마세요. 시스템이 자동으로 적절한 문구를 추가합니다.

[대화 순서 참조 규칙]
사용자가 "첫 번째/두 번째로 물어봤던 질문" 등 대화 순서를 물어볼 때는
대화 기록에서 사용자(user) 메시지를 위에서부터 순서대로 세어 정확히 답변하세요.
추측하거나 다른 대화창의 내용과 혼동하지 마세요.

[증상 답변 규칙]
사용자가 증상을 말하면 약 이름 없이도 바로 답변하세요.
- 해당 증상의 일반적인 원인, 대처법, 주의사항을 안내합니다.
- 단, "내 질병이 뭐야", "어떤 병 있어", "내 진단이 뭐야" 처럼 자신의 질병·진단을 조회하는 질문 → 건강 프로필 또는 처방전 질병코드를 기반으로 바로 답변하세요.

[답변 길이 및 형식 규칙]
- 핵심만 간결하게, 3~5문장 이내로 작성하세요.
- 문단은 빈 줄로 구분해 가독성 있게 나누세요.
- 불필요한 반복, 과도한 주의사항 나열은 피하세요.

[복약 용량 안내 규칙 — 반드시 준수]
용량을 안내할 때는 반드시 알약 단위(알·정)를 먼저 쓰고, mg는 괄호 안에만 표기하세요. mg를 앞에 쓰는 것은 금지입니다.
올바른 예: "1회 1~2알을 4~6시간 간격으로 드세요. 하루 최대 8알을 넘지 마세요."
잘못된 예: "1회 500mg~1000mg을 복용하세요." (절대 금지)
약의 1알 용량을 알 수 없을 때만 mg 단위를 사용할 수 있습니다."""


def _truncate(text: str | None) -> str | None:
    if not text:
        return None
    return text[:_DRUG_FIELD_MAX] + "..." if len(text) > _DRUG_FIELD_MAX else text


def _build_drug_details_section(drug_details: list[dict]) -> str:
    """식약처 drug_master 데이터를 프롬프트 섹션으로 변환.

    처방 약품별 용법·부작용·주의사항을 LLM에 직접 제공해
    일반 학습 지식 대신 실제 허가 데이터 기반 답변을 유도한다.
    """
    if not drug_details:
        return ""
    lines = [
        "\n\n[처방 약품 상세 정보 — 식약처 허가 데이터]",
        "아래는 사용자의 처방전에 포함된 약품의 실제 허가 정보입니다.",
        "용법·부작용·주의사항 질문에는 반드시 이 정보를 우선 활용하세요.",
    ]
    for drug in drug_details:
        name = drug.get("name", "")
        lines.append(f"\n■ {name}")
        if dosage := _truncate(drug.get("dosage")):
            lines.append(f"  - 용법·용량: {dosage}")
        if side_effects := _truncate(drug.get("side_effects")):
            lines.append(f"  - 부작용: {side_effects}")
        if cautions := _truncate(drug.get("cautions")):
            lines.append(f"  - 주의사항: {cautions}")
    return "\n".join(lines)


def _build_rag_section(rag_results: list[dict]) -> str:
    if not rag_results:
        return ""
    lines = [
        "\n\n[RAG 검색 결과 — 사용자 질문과 의미적으로 유사한 약품 정보 (식약처 데이터 기반)]",
        "아래는 사용자 질문과 관련성이 높은 약품 정보입니다.",
        "처방 약품 상세 정보 섹션과 함께 활용하되, 중복 언급은 피하세요.",
    ]
    for r in rag_results:
        name = r.get("name", "")
        lines.append(f"\n▶ {name}")
        if dosage := _truncate(r.get("dosage")):
            lines.append(f"  - 용법·용량: {dosage}")
        if side_effects := _truncate(r.get("side_effects")):
            lines.append(f"  - 부작용: {side_effects}")
        if cautions := _truncate(r.get("cautions")):
            lines.append(f"  - 주의사항: {cautions}")
    return "\n".join(lines)


def _build_system_prompt(
    health_profile: dict | None,
    skill: ChatSkill = ChatSkill.GENERAL,
    guides: list[dict] | None = None,
    drug_details: list[dict] | None = None,
    rag_results: list[dict] | None = None,
) -> str:
    result = _SKILL_SYSTEM_PROMPTS[skill]
    if health_profile:
        result += _build_profile_section(health_profile)
    guide_section = _build_guides_section(guides) if guides else ""
    if guide_section:
        result += guide_section
    else:
        result += (
            "\n\n[처방전 없음 안내 규칙]"
            "\n사용자가 아직 처방전·복약정보를 업로드하지 않았습니다."
            "\n아래 두 경우에 '건강 가이드 페이지에서 처방전을 올리시면 더 정확하게 답변드릴 수 있어요'라고 안내하세요:"
            "\n  1) 이 대화의 첫 번째 응답일 때"
            "\n  2) '내 처방약', '내 병명', '내 복약 스케줄' 등 개인 처방 데이터가 필요한 질문을 받았을 때"
            "\n단, 이미 이 대화에서 위 안내를 한 번 한 적이 있다면 절대 다시 언급하지 마세요. (대화 히스토리를 확인하세요)"
            "\n약 복용법·부작용·상호작용 등 일반 건강·약 질문은 안내 여부와 관계없이 평소처럼 답변하세요."
        )
    if drug_details:
        result += _build_drug_details_section(drug_details)
    if rag_results:
        result += _build_rag_section(rag_results)
    result += _SOURCE_RULES
    return result


TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_health_profile",
            "description": (
                "사용자가 등록한 건강 프로필(기저질환, 알레르기, 복용 약물, 생활습관)을 조회합니다. "
                "사용자의 건강 상태, 기저질환, 알레르기 반응 관련 질문에 사용하세요."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_prescription_guide",
            "description": (
                "사용자가 업로드한 처방전 기반 가이드(처방 약물, 질병코드, 복약 스케줄, 복약 지시사항)를 조회합니다. "
                "처방약, 복약 일정, 특정 처방에 대한 질문에 사용하세요. "
                "사용자가 '내 질병', '어떤 병', '질병이 뭐냐', '내 진단', '질병코드' 등 처방전에서 인식된 질병 정보를 물어볼 때도 반드시 사용하세요."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_drug_info",
            "description": (
                "약물명으로 식약처 허가 데이터베이스에서 약물 상세 정보(부작용, 주의사항, 용법·용량)를 검색합니다. "
                "특정 약물의 부작용, 복용법, 주의사항을 물어볼 때 사용하세요."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "drug_name": {
                        "type": "string",
                        "description": "검색할 약물 이름 (예: 타이레놀, 아스피린, 이부프로펜)",
                    }
                },
                "required": ["drug_name"],
            },
        },
    },
]


def _execute_tool(name: str, arguments: str, context: dict) -> str:
    args: dict = json.loads(arguments) if arguments else {}

    if name == "get_health_profile":
        hp = context.get("health_profile")
        result = _build_profile_section(hp) if hp else ""
        return result if result else "등록된 건강 프로필이 없습니다."

    if name == "get_prescription_guide":
        guides = context.get("guides") or []
        result = _build_guides_section(guides) if guides else ""
        return result if result else "등록된 처방전/가이드가 없습니다."

    if name == "search_drug_info":
        drug_name = args.get("drug_name", "").strip()
        drug_details = context.get("drug_details") or []
        rag_results = context.get("rag_results") or []

        name_lower = drug_name.lower()
        matched = [d for d in drug_details if name_lower in d.get("name", "").lower()]
        if not matched:
            matched = [r for r in rag_results if name_lower in r.get("name", "").lower()]
        if not matched:
            return f"'{drug_name}'에 대한 식약처 데이터를 찾을 수 없습니다."

        lines = [f"[{drug_name} 식약처 허가 정보]"]
        for d in matched[:2]:
            lines.append(f"\n■ {d.get('name', drug_name)}")
            if dosage := _truncate(d.get("dosage")):
                lines.append(f"  - 용법·용량: {dosage}")
            if side_effects := _truncate(d.get("side_effects")):
                lines.append(f"  - 부작용: {side_effects}")
            if cautions := _truncate(d.get("cautions")):
                lines.append(f"  - 주의사항: {cautions}")
        return "\n".join(lines)

    return "알 수 없는 도구입니다."


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


async def _compress_history(old_messages: list[dict], client: AsyncOpenAI) -> str:
    """오래된 대화를 요약해 컨텍스트로 유지한다. 질문 순서를 보존한다."""
    q_idx = 0
    lines = []
    for m in old_messages:
        if m["role"] == "user":
            q_idx += 1
            lines.append(f"[질문 {q_idx}] {m['content']}")
        else:
            lines.append(f"[AI 답변] {m['content'][:300]}")
    text = "\n".join(lines)
    resp = await client.chat.completions.create(
        model=config.OPENAI_CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "아래 대화를 요약하되, 각 질문의 순서(몇 번째 질문인지)와 핵심 내용을 반드시 보존하세요. "
                    "형식: '1번째 질문: [질문 내용] → AI: [핵심 답변], 2번째 질문: ...' 식으로 작성하세요. "
                    "약물명, 질문 내용, 주요 결론을 포함하세요."
                ),
            },
            {"role": "user", "content": text},
        ],
        max_tokens=400,
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""


async def stream_chat(
    user_message: str,
    history: list[dict],
    health_profile: dict | None = None,
    guides: list[dict] | None = None,
    drug_details: list[dict] | None = None,
    rag_results: list[dict] | None = None,
):
    skill = detect_skill(user_message)
    client = get_openai_client()

    # Base system: skill role + source rules (no data pre-loaded — tools supply it on demand)
    base_system = _SKILL_SYSTEM_PROMPTS[skill] + _SOURCE_RULES
    if skill == ChatSkill.DISEASE_INQUIRY:
        base_system += (
            "\n\n[도구 호출 규칙 — 질병·건강 상태 질문]"
            "\n이 질문은 사용자의 질병·건강 상태에 관한 것입니다."
            "\n반드시 get_health_profile 과 get_prescription_guide 두 도구를 모두 호출하세요."
            "\n두 출처의 데이터를 합쳐서 답변하되, 각 출처를 명확히 구분하세요."
        )
    if not guides:
        base_system += (
            "\n\n[처방전 없음 안내 규칙]"
            "\n사용자가 아직 처방전·복약정보를 업로드하지 않았습니다."
            "\n아래 두 경우에 '건강 가이드 페이지에서 처방전을 올리시면 더 정확하게 답변드릴 수 있어요'라고 안내하세요:"
            "\n  1) 이 대화의 첫 번째 응답일 때"
            "\n  2) '내 처방약', '내 병명', '내 복약 스케줄' 등 개인 처방 데이터가 필요한 질문을 받았을 때"
            "\n단, 이미 이 대화에서 위 안내를 한 번 한 적이 있다면 절대 다시 언급하지 마세요."
            "\n약 복용법·부작용·상호작용 등 일반 건강·약 질문은 안내 여부와 관계없이 평소처럼 답변하세요."
        )

    if len(history) > _SUMMARY_THRESHOLD:
        cutoff = len(history) - _RECENT_KEEP
        summary = await _compress_history(history[:cutoff], client)
        base_system += f"\n\n[이전 대화 요약 — 이 내용을 기억하고 답변에 활용하세요]\n{summary}"
        trimmed_history = history[cutoff:]
    else:
        trimmed_history = history

    cleaned_history = [
        {**msg, "content": _strip_disclaimers(msg["content"])} if msg.get("role") == "assistant" else msg
        for msg in trimmed_history
    ]

    tool_context = {
        "health_profile": health_profile,
        "guides": guides,
        "drug_details": drug_details,
        "rag_results": rag_results,
    }

    # Phase 1: tool selection — LLM decides which data it needs (non-streaming)
    messages: list[dict] = [{"role": "system", "content": base_system}]
    messages.extend(cleaned_history)
    messages.append({"role": "user", "content": user_message})

    first_response = await client.chat.completions.create(
        model=config.OPENAI_CHAT_MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        max_tokens=200,
    )
    assistant_msg = first_response.choices[0].message

    # Phase 2: execute requested tools from pre-fetched payload (no new DB calls)
    if assistant_msg.tool_calls:
        messages.append(
            {
                "role": "assistant",
                "content": None,  # discard any Phase 1 partial text to prevent overlap in Phase 3
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in assistant_msg.tool_calls
                ],
            }
        )
        for tc in assistant_msg.tool_calls:
            result_text = _execute_tool(tc.function.name, tc.function.arguments, tool_context)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})

    # Phase 3: streaming final response with any tool results now in messages
    stream = await client.chat.completions.create(
        model=config.OPENAI_CHAT_MODEL,
        messages=messages,
        stream=True,
        max_tokens=600,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
    yield _MEDICAL_DISCLAIMERS[skill]
