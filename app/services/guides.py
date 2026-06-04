import asyncio
import html
import json
import os
import pathlib
import re
import uuid
from datetime import UTC, datetime

# client = AsyncOpenAI(
#     api_key=os.getenv("OPENAI_API_KEY"),
# )
import pandas as pd
from fastapi import HTTPException, status
from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.sqlalchemy_client import _AsyncSessionFactory
from app.dtos.guides import (
    DietGuide,
    ExerciseGuide,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackStatusResponse,
    GenerateGuideRequest,
    GenerateGuideResponse,
    GuideContextResponse,
    GuideGenerationResult,
    GuideGenerationStatus,
    GuideResponse,
    GuideStatusResponse,
    GuideType,
    JobStatus,
    LifestyleGuide,
    MedicationDetail,
    MedicationGuide,
    MedicationItem,
    MedicationMatchStatus,
    UpdateFeedbackStatusRequest,
)
from app.models.drug_master import DrugMaster

# ── In-memory 저장소 ──────────────────────────────────────────────────────────
_jobs: dict[str, dict] = {}
_guides: dict[str, dict] = {}
_feedbacks: dict[str, dict] = {}

# ── 식약처 CSV 싱글턴 ─────────────────────────────────────────────────────────
_CSV_PATH = pathlib.Path(__file__).parent.parent / "data" / "식약처_의약품개요정보_전체누적본.csv"
_drug_df: pd.DataFrame | None = None


def _get_drug_df() -> pd.DataFrame:
    global _drug_df
    if _drug_df is None:
        _drug_df = pd.read_csv(_CSV_PATH, encoding="utf-8-sig")
    return _drug_df


# ── 제품허가정보 CSV 싱글턴 (optional fallback) ────────────────────────────────
_MASTER_CSV_PATH = pathlib.Path(__file__).parent.parent / "data" / "all_drugs_master.csv"
_master_drug_df: pd.DataFrame | None = None
_master_csv_unavailable: bool = False


def _get_master_drug_df() -> pd.DataFrame | None:
    global _master_drug_df, _master_csv_unavailable
    if _master_csv_unavailable:
        return None
    if _master_drug_df is None:
        if not _MASTER_CSV_PATH.exists():
            _master_csv_unavailable = True
            return None
        try:
            _master_drug_df = pd.read_csv(_MASTER_CSV_PATH, encoding="utf-8-sig")
        except Exception:
            _master_csv_unavailable = True
            return None
    return _master_drug_df


# ── CSV 매핑 헬퍼 ─────────────────────────────────────────────────────────────


def _safe_str(val: object) -> str:
    s = str(val).strip()
    return s if s and s.lower() != "nan" else ""


def _strip_html(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _shorten_text(text: str, limit: int = 120) -> str:
    text = text.replace("\n", " ").strip()
    return text[:limit] + "..." if len(text) > limit else text


def _make_medication_action_icons(cautions: list[str], side_effects: list[str], storage: str = "") -> list[dict]:
    text = " ".join(cautions + side_effects + [storage])

    icons = []

    if any(keyword in text for keyword in ["임부", "임신", "수유"]):
        icons.append({"type": "pregnancy", "label": "임부·수유부 주의"})

    if any(keyword in text for keyword in ["알코올", "음주", "술"]):
        icons.append({"type": "alcohol", "label": "알코올 X"})

    if "자몽" in text:
        icons.append({"type": "grapefruit", "label": "자몽주스 X"})

    if any(keyword in text for keyword in ["졸음", "어지러움", "현기증"]):
        icons.append({"type": "drowsiness", "label": "졸음·어지러움 주의"})

    if any(keyword in text for keyword in ["운전", "기계 조작", "기계조작"]):
        icons.append({"type": "driving", "label": "운전 주의"})

    if any(keyword in text for keyword in ["두통"]):
        icons.append({"type": "headache", "label": "두통 가능"})

    if any(keyword in text for keyword in ["간손상", "간장애", "간질환", "간 기능"]):
        icons.append({"type": "liver", "label": "간 질환 상담"})

    if any(keyword in text for keyword in ["신장", "콩팥", "신장애"]):
        icons.append({"type": "kidney", "label": "신장 질환 상담"})

    if any(keyword in text for keyword in ["어린이의 손이 닿지 않는 곳"]):
        icons.append({"type": "child_storage", "label": "어린이 손 닿지 않게 보관"})

    return icons


def _make_medication_usage_icons(dosage: str) -> list[dict]:
    icons = []

    if any(keyword in dosage for keyword in ["4~6시간", "4-6시간"]):
        icons.append({"type": "interval", "label": "4~6시간 간격"})

    if any(keyword in dosage for keyword in ["1일 5회", "초과"]):
        icons.append({"type": "max_dose", "label": "1일 최대횟수 주의"})

    if any(keyword in dosage for keyword in ["물 없이"]):
        icons.append({"type": "no_water", "label": "물 없이 복용 가능"})

    if any(keyword in dosage for keyword in ["몸무게", "체중"]):
        icons.append({"type": "weight", "label": "체중 기준 용량 확인"})

    return icons


def _row_to_medication_item(row: pd.Series) -> MedicationItem:
    dosage = _safe_str(row.get("useMethodQesitm"))
    storage = _safe_str(row.get("depositMethodQesitm"))
    side_effects_str = _safe_str(row.get("seQesitm"))

    cautions = [
        c
        for c in [
            _safe_str(row.get("atpnWarnQesitm")),
            _safe_str(row.get("atpnQesitm")),
            _safe_str(row.get("intrcQesitm")),
        ]
        if c
    ]

    return MedicationItem(
        name=_safe_str(row.get("itemName")),
        dosage=dosage,
        timing="",
        before_after_meal="",
        side_effects=[side_effects_str] if side_effects_str else [],
        cautions=cautions,
        missed_dose="",
        storage=storage,
        action_icons=_make_medication_action_icons(
            cautions,
            [side_effects_str] if side_effects_str else [],
            storage,
        ),
        usage_icons=_make_medication_usage_icons(dosage),
        easy_summary=_make_easy_summary(
            cautions,
            side_effects_str,
            dosage,
            storage,
        ),
        match_status=MedicationMatchStatus.EXACT_DB_MATCH,
        source_name="식약처 의약품개요정보",
        disclaimer=None,
    )


def _make_easy_summary(
    cautions: list[str],
    side_effects: str,
    dosage: str,
    storage: str = "",
) -> list[str]:
    text = " ".join(cautions + [side_effects, dosage, storage])

    summaries = []

    if any(keyword in text for keyword in ["알코올", "음주", "술"]):
        summaries.append("술과 함께 복용하지 마세요.")

    if any(keyword in text for keyword in ["간손상", "간장애", "간질환", "간 기능"]):
        summaries.append("간 질환이 있으면 복용 전 전문가와 상담하세요.")

    if any(keyword in text for keyword in ["신장", "콩팥", "신장애"]):
        summaries.append("신장 질환이 있으면 복용 전 전문가와 상담하세요.")

    if any(keyword in text for keyword in ["4~6시간", "4-6시간"]):
        summaries.append("복용 간격을 지켜 주세요.")

    if any(keyword in text for keyword in ["1일 5회", "초과"]):
        summaries.append("하루 최대 복용 횟수를 넘기지 마세요.")

    if any(keyword in text for keyword in ["몸무게", "체중"]):
        summaries.append("아이들은 체중 기준 용량 확인이 중요해요.")

    if any(keyword in text for keyword in ["어린이의 손이 닿지 않는 곳"]):
        summaries.append("어린이 손이 닿지 않는 곳에 보관하세요.")

    return summaries


_DEFAULT_SUMMARY_PROMPT = (
    "당신은 복약 정보를 환자 친화적인 한국어로 요약하는 도우미입니다.\n"
    "반드시 아래 규칙을 따르세요:\n"
    "- 제공된 데이터에 없는 약효, 진단, 처방 정보를 절대 추가하지 마세요.\n"
    "- 환자가 실제로 해야 할 복약 행동 중심으로 짧고 명확하게 설명하세요.\n"
    "- '의사와 상담' 또는 '전문가와 상담' 문장이 여러 개 나올 경우 하나로 통합하세요.\n"
    "- '반드시 의사와 상담하세요' 같은 강한 표현 대신 '이상 증상이 있으면 의료진과 상담하세요' 형태를 사용하세요.\n"
    "- 추상적이거나 막연한 표현보다 구체적인 행동 문장을 우선하세요.\n"
    "- 3~5개의 독립적인 짧은 문장으로만 작성하세요.\n"
    '- 응답은 반드시 JSON 형식으로: {"sentences": ["문장1", "문장2", ...]}'
)

_PATIENT_SUMMARY_PROMPT = (
    "당신은 이미 처방받은 환자가 집에서 약을 올바르게 복용하도록 돕는 도우미입니다.\n"
    "반드시 아래 규칙을 따르세요:\n"
    "- 이미 처방받은 환자 대상이므로, 처방 여부나 용량을 다시 결정하는 표현은 절대 사용하지 마세요.\n"
    "- 복용 중 주의사항과 실제 복약 행동 중심으로 설명하세요.\n"
    "- 복용 횟수·방법, 식사 관계, 임신/수유 주의, 간·신장 주의, 어린이 사용 주의를 우선 포함하세요.\n"
    "- '복용 전 상담' 표현은 사용하지 마세요.\n"
    "- 복용 기간 연장, 병용요법, 용량 조절은 환자가 임의로 결정할 수 있는 것처럼 작성하지 마세요.\n"
    "- 복용 방법·기간에 대해서는 '처방받은 기간과 방법을 지켜 복용하세요' 또는 '의료진 안내를 따르세요' 형태를 우선 사용하세요.\n"
    "- 다음 내용은 절대 포함하지 마세요:\n"
    "  * 치료 전환이나 약 변경 관련 표현\n"
    "  * 임상시험·연구 설명\n"
    "  * 허가·승인·처방 문체\n"
    "  * 의사·약사 전용 표현\n"
    "  * 초기 용량 조절 관련 표현\n"
    "  * 환자가 임의로 복용 기간을 연장하거나 병용을 결정하는 표현\n"
    "- 제공된 데이터에 없는 약효, 진단, 처방 정보를 절대 추가하지 마세요.\n"
    "- 3~5개의 독립적인 짧은 문장으로만 작성하세요.\n"
    '- 응답은 반드시 JSON 형식으로: {"sentences": ["문장1", "문장2", ...]}'
)

_BAD_PHRASES_WEB_REFERENCE = [
    "전환할 수 있",
    "초기 용량",
    "임상시험",
    "복용 전 의료진",
    "복용 전 상담",
    "더 복용할 수 있",
    "병용요법으로",
]

_FALLBACK_KEY_INSTRUCTIONS = [
    "식후 복용을 반드시 지켜주세요.",
    "음주 중 복용을 삼가세요.",
    "증상 악화 시 즉시 의사와 상담하세요.",
]


def _filter_patient_summary(sentences: list[str]) -> list[str]:
    return [s for s in sentences if not any(phrase in s for phrase in _BAD_PHRASES_WEB_REFERENCE)]


async def _make_easy_summary_llm(
    dosage: str,
    cautions: list[str],
    side_effects: list[str],
    storage: str,
    system_prompt: str = _DEFAULT_SUMMARY_PROMPT,
) -> list[str]:
    parts: list[str] = []
    if dosage:
        parts.append(f"용법·용량: {dosage}")
    if cautions:
        parts.append(f"주의사항: {'; '.join(cautions)}")
    if side_effects:
        parts.append(f"이상반응: {'; '.join(side_effects)}")
    if storage:
        parts.append(f"보관방법: {storage}")
    if not parts:
        return []

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": f"다음 의약품 공식 정보를 환자가 이해하기 쉽게 요약해주세요:\n\n{chr(10).join(parts)}",
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=400,
        temperature=0.3,
    )
    result = json.loads(response.choices[0].message.content)
    sentences = result.get("sentences", [])
    return [str(s) for s in sentences[:5]] if isinstance(sentences, list) else []


async def _enrich_easy_summary(item: MedicationItem) -> list[str]:
    if item.match_status == MedicationMatchStatus.NOT_FOUND:
        return item.easy_summary
    if not os.getenv("OPENAI_API_KEY"):
        return item.easy_summary
    is_web_ref = item.match_status == MedicationMatchStatus.WEB_REFERENCE
    prompt = _PATIENT_SUMMARY_PROMPT if is_web_ref else _DEFAULT_SUMMARY_PROMPT
    try:
        result = await _make_easy_summary_llm(
            item.dosage,
            item.cautions,
            item.side_effects,
            item.storage,
            system_prompt=prompt,
        )
        if is_web_ref:
            result = _filter_patient_summary(result)
        return result if result else item.easy_summary
    except Exception:
        return item.easy_summary


def _normalize_drug_name(name: str) -> str:
    n = name.strip().lower().replace(" ", "")
    # .lower() 이후이므로 이미 소문자이지만 re.IGNORECASE로 명시적 처리 (40mg, 40MG 모두 대응)
    n = re.sub(r"(\d)mg\b", r"\1밀리그램", n, flags=re.IGNORECASE)
    n = re.sub(r"(\d)mcg\b", r"\1마이크로그램", n, flags=re.IGNORECASE)
    n = re.sub(r"(\d)ml\b", r"\1밀리리터", n, flags=re.IGNORECASE)
    n = re.sub(r"[캡캅]셀", "캡슐", n)
    return n


def _search_medication_master(name: str) -> MedicationItem | None:
    df = _get_master_drug_df()
    if df is None:
        return None
    normalized = _normalize_drug_name(name)
    mask = (
        df["ITEM_NAME"]
        .astype(str)
        .str.lower()
        .str.replace(" ", "", regex=False)
        .str.contains(normalized, na=False, regex=False)
    )
    matches = df[mask]
    if matches.empty:
        return None
    row = matches.iloc[0]
    dosage = _strip_html(_safe_str(row.get("UD_DOC_DATA")))
    cautions_str = _strip_html(_safe_str(row.get("NB_DOC_DATA")))
    if len(cautions_str) > 1500:
        cautions_str = cautions_str[:1500] + "... (제품허가정보 원문 일부)"
    cautions = [cautions_str] if cautions_str else []
    return MedicationItem(
        name=_safe_str(row.get("ITEM_NAME")),
        dosage=dosage,
        timing="",
        before_after_meal="",
        side_effects=[],
        cautions=cautions,
        missed_dose="",
        storage="",
        action_icons=_make_medication_action_icons(cautions, [], ""),
        usage_icons=_make_medication_usage_icons(dosage),
        easy_summary=_make_easy_summary(cautions, "", dosage),
        match_status=MedicationMatchStatus.WEB_REFERENCE,
        source_name="제품허가정보",
        disclaimer=None,
    )


def _search_medication(name: str) -> MedicationItem:
    df = _get_drug_df()
    normalized = _normalize_drug_name(name)
    mask = (
        df["itemName"]
        .astype(str)
        .str.lower()
        .str.replace(" ", "", regex=False)
        .str.contains(normalized, na=False, regex=False)
    )
    matches = df[mask]
    if matches.empty:
        master_result = _search_medication_master(name)
        if master_result:
            return master_result
        return MedicationItem(
            name=name,
            dosage="",
            timing="",
            before_after_meal="",
            side_effects=[],
            cautions=[],
            missed_dose="",
            storage="",
            match_status=MedicationMatchStatus.NOT_FOUND,
            disclaimer="해당 의약품 정보를 데이터베이스에서 찾을 수 없습니다.",
            source_name=None,
        )
    return _row_to_medication_item(matches.iloc[0])


async def _search_medication_db(session: AsyncSession, name: str) -> MedicationItem | None:
    """drug_master DB에서 약물 조회. 없거나 오류 시 None 반환."""
    normalized = _normalize_drug_name(name)
    try:
        result = await session.execute(
            select(DrugMaster)
            .where(func.word_similarity(normalized, DrugMaster.item_name) > 0.6)
            .order_by(func.word_similarity(normalized, DrugMaster.item_name).desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
    except Exception:
        return None
    if row is None:
        return None

    dosage = row.dosage or ""
    cautions_str = row.cautions or ""
    side_effects_str = row.side_effects or ""
    storage = row.storage or ""
    cautions = [cautions_str] if cautions_str else []
    match_status = (
        MedicationMatchStatus.EXACT_DB_MATCH if row.source == "식약처" else MedicationMatchStatus.WEB_REFERENCE
    )
    return MedicationItem(
        name=row.item_name,
        dosage=dosage,
        timing="",
        before_after_meal="",
        side_effects=[side_effects_str] if side_effects_str else [],
        cautions=cautions,
        missed_dose="",
        storage=storage,
        action_icons=_make_medication_action_icons(
            cautions,
            [side_effects_str] if side_effects_str else [],
            storage,
        ),
        usage_icons=_make_medication_usage_icons(dosage),
        easy_summary=_make_easy_summary(cautions, side_effects_str, dosage, storage),
        match_status=match_status,
        source_name=row.source or "DB",
        disclaimer=None,
    )


def _build_schedule_table(medications: list[MedicationDetail]) -> list[dict]:
    schedule: dict[str, list[str]] = {}
    for med in medications:
        name = med.medication_name
        if med.timing:
            schedule.setdefault(med.timing, []).append(name)
        elif med.time_of_day:
            for slot in med.time_of_day:
                schedule.setdefault(str(slot), []).append(name)
        else:
            schedule.setdefault("복용 시간 확인 필요", []).append(name)
    return [{"time": t, "medications": names} for t, names in schedule.items()]


async def _make_medication_guide_from_csv(
    medication_names: list[str],
    session: AsyncSession | None = None,
) -> MedicationGuide:
    items: list[MedicationItem] = []
    seen_names: set[str] = set()
    for name in medication_names:
        item: MedicationItem | None = None
        if session is not None:
            item = await _search_medication_db(session, name)
        if item is None:
            item = MedicationItem(
                name=name,
                dosage="",
                timing="",
                before_after_meal="",
                side_effects=[],
                cautions=[],
                missed_dose="",
                storage="",
                match_status=MedicationMatchStatus.NOT_FOUND,
                disclaimer="해당 의약품 정보를 데이터베이스에서 찾을 수 없습니다.",
                source_name=None,
            )
        if item.name not in seen_names:
            seen_names.add(item.name)
            items.append(item)
    enriched_summaries = await asyncio.gather(*[_enrich_easy_summary(item) for item in items])
    for item, summary in zip(items, enriched_summaries, strict=True):
        item.easy_summary = summary
    return MedicationGuide(medications=items)


async def _build_medication_guide(
    medication_names: list[str],
    guide_types: list[GuideType],
) -> MedicationGuide | None:
    """DB 우선 조회로 MEDICATION 가이드 생성. guide_types에 MEDICATION 없으면 None."""
    if GuideType.MEDICATION not in guide_types:
        return None
    async with _AsyncSessionFactory() as db_session:
        return await _make_medication_guide_from_csv(medication_names, db_session)


# ── Mock 데이터 생성 헬퍼 (LIFESTYLE / DIET / EXERCISE) ──────────────────────


def _make_lifestyle_guide() -> LifestyleGuide:
    return LifestyleGuide(
        tips=[
            "하루 7~8시간 충분한 수면을 취하세요.",
            "스트레스를 줄이고 규칙적인 생활 패턴을 유지하세요.",
            "금연·금주를 권장합니다.",
            "복약 중 졸음이 올 수 있으니 운전 및 기계 조작 시 주의하세요.",
        ]
    )


def _make_diet_guide() -> DietGuide:
    return DietGuide(
        forbidden=["알코올", "자몽 주스", "고지방 음식"],
        recommended=["통곡물", "채소류", "저지방 단백질 (닭가슴살, 두부)"],
        hydration="하루 1.5~2L 물 섭취를 권장합니다.",
    )


def _make_exercise_guide() -> ExerciseGuide:
    return ExerciseGuide(
        intensity="저강도 (가벼운 걷기·스트레칭)",
        frequency="주 3~5회",
        duration="1회 20~30분",
        cautions=[
            "복약 후 어지러움이 있을 경우 즉시 운동 중단",
            "통증 발생 시 휴식 우선",
            "격렬한 유산소 운동은 증상 완화 후 재개",
        ],
    )


_FALLBACK_DIET = _make_diet_guide()
_FALLBACK_EXERCISE = _make_exercise_guide()

# ── Whitelist 질환 필터 (llm-guide-policy.md §8) ──────────────────────────────

_DISEASE_WHITELIST_ICD_PREFIXES: tuple[str, ...] = (
    "I10",
    "I11",
    "I12",
    "I13",  # 고혈압
    "E11",
    "E12",
    "E13",
    "E14",  # 당뇨
    "E78",  # 고지혈증
    "K29",  # 위염
    "K21",  # 역류성식도염
    "K59.0",  # 변비
    "M15",
    "M16",
    "M17",
    "M18",
    "M19",  # 골관절염
    "J30",  # 알레르기비염
)

_DISEASE_WHITELIST_NAME_KEYWORDS: tuple[str, ...] = (
    "고혈압",
    "당뇨",
    "고지혈증",
    "위염",
    "역류성식도염",
    "변비",
    "골관절염",
    "알레르기비염",
)

_GENERIC_GUIDE_NOTICE = (
    "현재 인식된 질환 정보가 가이드 생성 지원 범위에 포함되지 않아, 일반적인 건강관리 안내를 제공합니다."
)


async def _make_exercise_guide_with_llm(
    medication_names: list[str],
    disease_codes: list[str],
    disease_names: list[str],
) -> ExerciseGuide:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = AsyncOpenAI(api_key=api_key)

    if disease_names:
        disease_entries = [
            f"{code} - {name}" if name else code for code, name in zip(disease_codes, disease_names, strict=False)
        ]
    else:
        disease_entries = disease_codes

    prompt = f"""
아래 약물과 질병 정보를 참고하여 환자 운동 가이드를 JSON으로 작성하세요.

출력 형식 (아래 JSON만 출력, 추가 설명 없이):
{{
  "intensity": "운동 강도 한 구절",
  "frequency": "운동 빈도 한 구절",
  "duration": "1회 운동 시간 한 구절",
  "cautions": ["주의사항 2~4가지"]
}}

조건:
- 환자가 이해하기 쉬운 한국어 사용
- 질병 정보가 있으면 해당 질환의 특성을 intensity와 cautions에 반영할 것
- 질병 정보가 있으면 해당 질환과 관련된 일반 주의사항을 cautions에 1개 이상 반드시 포함할 것
  (예: 혈압 관련이면 심박수 급상승 주의, 소화기 질환이면 식후 즉시 운동 피하기 등)
- 질병 정보가 없거나 불명확하면 저강도 운동 중심으로 작성
- 무리한 운동이나 고강도 운동을 권장하지 말 것
- 통증, 어지러움, 흉통, 호흡곤란 발생 시 운동 중단 안내 포함 가능
- 질병코드에 없는 새로운 질환이나 신체부위를 추가하지 말 것
- 확정 진단처럼 표현하지 말 것
- 재활치료, 전문 운동처방 수준의 구체적인 지시는 하지 말 것
- 일반적인 생활관리 수준의 운동 가이드만 작성할 것
- 특정 운동 동작(팔 들기, 스쿼트, 계단 오르기 등)을 구체적으로 지시하지 말 것

약물:
{", ".join(medication_names) if medication_names else "정보 없음"}

질병 정보 (OCR 추출 참고정보):
{", ".join(disease_entries) if disease_entries else "정보 없음"}
"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 환자 친화적인 운동 가이드를 작성하는 의료 AI입니다."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.5,
    )

    data = json.loads(response.choices[0].message.content or "{}")

    intensity = data.get("intensity")
    frequency = data.get("frequency")
    duration = data.get("duration")
    cautions = data.get("cautions")

    return ExerciseGuide(
        intensity=intensity if isinstance(intensity, str) and intensity.strip() else _FALLBACK_EXERCISE.intensity,
        frequency=frequency if isinstance(frequency, str) and frequency.strip() else _FALLBACK_EXERCISE.frequency,
        duration=duration if isinstance(duration, str) and duration.strip() else _FALLBACK_EXERCISE.duration,
        cautions=cautions if isinstance(cautions, list) and cautions else _FALLBACK_EXERCISE.cautions,
    )


async def _make_diet_guide_with_llm(
    medication_names: list[str],
    disease_codes: list[str],
    disease_names: list[str],
) -> DietGuide:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = AsyncOpenAI(api_key=api_key)

    if disease_names:
        disease_entries = [
            f"{code} - {name}" if name else code for code, name in zip(disease_codes, disease_names, strict=False)
        ]
    else:
        disease_entries = disease_codes

    prompt = f"""
아래 약물과 질병 정보를 참고하여 환자 식사 가이드를 JSON으로 작성하세요.

출력 형식 (아래 JSON만 출력, 추가 설명 없이):
{{
  "forbidden": ["피해야 할 음식 또는 성분 2~4가지"],
  "recommended": ["권장 음식 또는 성분 2~4가지"],
  "hydration": "수분 섭취 안내 한 문장"
}}

조건:
- 환자가 이해하기 쉬운 한국어 사용
- 질병 정보가 있으면 해당 질환에 적합한 식사 안내를 일반 안내보다 우선
- 질병코드 기반 확정 진단 표현 금지
- 질병코드에 없는 새로운 질환이나 증상을 추가하지 말 것
- 안전한 생활관리 수준으로만 작성

약물:
{", ".join(medication_names) if medication_names else "정보 없음"}

질병 정보 (OCR 추출 참고정보):
{", ".join(disease_entries) if disease_entries else "정보 없음"}
"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 환자 친화적인 식사 가이드를 작성하는 의료 AI입니다."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.5,
    )

    data = json.loads(response.choices[0].message.content or "{}")

    forbidden = data.get("forbidden")
    recommended = data.get("recommended")
    hydration = data.get("hydration")

    return DietGuide(
        forbidden=forbidden if isinstance(forbidden, list) and forbidden else _FALLBACK_DIET.forbidden,
        recommended=recommended if isinstance(recommended, list) and recommended else _FALLBACK_DIET.recommended,
        hydration=hydration if isinstance(hydration, str) and hydration.strip() else _FALLBACK_DIET.hydration,
    )


async def _make_lifestyle_guide_with_llm(
    medication_names: list[str],
    disease_codes: list[str],
    disease_names: list[str],
) -> LifestyleGuide:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = AsyncOpenAI(api_key=api_key)

    # disease_names와 disease_codes를 같은 순서로 결합: "M75.3 - 어깨의 관절염" 또는 "M75.3"
    if disease_names:
        disease_entries = [
            f"{code} - {name}" if name else code for code, name in zip(disease_codes, disease_names, strict=False)
        ]
    else:
        disease_entries = disease_codes

    prompt = f"""
아래 약물과 질병 정보를 참고하여 생활관리 팁 4개를 작성하세요.

출력 형식:
- 팁 4개를 줄바꿈 목록으로 작성
- 각 항목은 행동 지침 문장 하나로만 작성
- 인사말, 제목, 도입문("다음은", "가이드입니다", "환자님" 등) 없이 바로 시작
- "생활관리 가이드", "다음은", "환자님" 같은 문구 출력 금지

내용 조건:
- 한국어로 작성
- 환자가 이해하기 쉬운 표현 사용
- 질병 정보가 있으면 해당 질환 관련 생활관리를 일반 건강정보보다 우선하여 작성
- 질병명 또는 질병코드에 명시되지 않은 신체 부위를 새로 만들지 말 것
- 부위가 불명확한 관절 질환은 "관절", "통증 부위", "불편한 부위" 같은 일반 표현 사용
- 질병분류기호는 OCR로 추출된 참고정보이며, 확정 진단으로 표현하지 말 것
- 질병코드에 근거해 새로운 진단명이나 치료 지시를 생성하지 말 것
- 약물명과 질병 정보를 함께 고려하되, 환자에게 안전한 생활관리 수준으로만 작성할 것

약물:
{", ".join(medication_names) if medication_names else "정보 없음"}

질병 정보 (OCR 추출 참고정보):
{", ".join(disease_entries) if disease_entries else "정보 없음"}
"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "당신은 환자 친화적인 복약 생활관리 가이드를 작성하는 의료 AI입니다.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.5,
    )

    content = response.choices[0].message.content or ""

    tips = [line.strip("-•1234567890. ").strip() for line in content.splitlines() if line.strip()]

    return LifestyleGuide(tips=tips)


def _filter_whitelist_diseases(
    disease_codes: list[str],
    disease_names: list[str],
) -> tuple[list[str], list[str]]:
    """llm-guide-policy.md §8 whitelist 기준으로 disease 쌍을 필터링."""
    filtered_codes: list[str] = []
    filtered_names: list[str] = []
    max_len = max(len(disease_codes), len(disease_names)) if (disease_codes or disease_names) else 0
    for i in range(max_len):
        code = disease_codes[i] if i < len(disease_codes) else ""
        name = disease_names[i] if i < len(disease_names) else ""
        code_match = bool(code) and any(code.startswith(p) for p in _DISEASE_WHITELIST_ICD_PREFIXES)
        name_match = bool(name) and any(kw in name for kw in _DISEASE_WHITELIST_NAME_KEYWORDS)
        if code_match or name_match:
            filtered_codes.append(code)
            filtered_names.append(name)
    return filtered_codes, filtered_names


async def _run_mock_worker(
    job_id: str,
    guide_id: str,
    guide_types: list[GuideType],
    medication_names: list[str],
    medications: list[MedicationDetail],
    disease_codes: list[str],
    disease_names: list[str],
) -> None:
    await asyncio.sleep(1)
    _jobs[job_id]["status"] = JobStatus.PROCESSING

    try:
        await asyncio.sleep(3)

        now = datetime.now(UTC).isoformat()

        generation_results = [
            GuideGenerationResult(guide_type=gt, status=GuideGenerationStatus.DONE) for gt in guide_types
        ]

        filtered_codes, filtered_names = _filter_whitelist_diseases(disease_codes, disease_names)
        needs_generic_notice = bool(disease_codes) and not filtered_codes

        if GuideType.LIFESTYLE in guide_types:
            try:
                lifestyle_guide = await _make_lifestyle_guide_with_llm(medication_names, filtered_codes, filtered_names)
            except Exception as e:
                print(f"LLM guide generation failed: {e}")
                lifestyle_guide = _make_lifestyle_guide()
            if needs_generic_notice:
                lifestyle_guide = LifestyleGuide(tips=[_GENERIC_GUIDE_NOTICE] + lifestyle_guide.tips)
        else:
            lifestyle_guide = None

        if GuideType.DIET in guide_types:
            try:
                diet_guide = await _make_diet_guide_with_llm(medication_names, filtered_codes, filtered_names)
            except Exception as e:
                print(f"LLM diet guide generation failed: {e}")
                diet_guide = _make_diet_guide()
        else:
            diet_guide = None

        if GuideType.EXERCISE in guide_types:
            try:
                exercise_guide = await _make_exercise_guide_with_llm(medication_names, filtered_codes, filtered_names)
            except Exception as e:
                print(f"LLM exercise guide generation failed: {e}")
                exercise_guide = _make_exercise_guide()
        else:
            exercise_guide = None

        medication_guide = await _build_medication_guide(medication_names, guide_types)

        guide = GuideResponse(
            guide_id=guide_id,
            guide_types=guide_types,
            created_at=now,
            medication_guide=medication_guide,
            schedule_table=(
                _build_schedule_table(medications)
                if medications
                else ([{"time": "복용 시간 확인 필요", "medications": medication_names}] if medication_names else None)
            ),
            lifestyle_guide=lifestyle_guide,
            diet_guide=diet_guide,
            exercise_guide=exercise_guide,
            generation_results=generation_results,
        )

        _guides[guide_id] = guide.model_dump()
        _guides[guide_id]["disease_codes"] = disease_codes
        _jobs[job_id]["status"] = JobStatus.DONE
        _jobs[job_id]["guide_id"] = guide_id

    except FileNotFoundError as e:
        error_message = f"필수 파일 없음: {e.filename}"
        print(f"[GuideWorker] job_id={job_id} {error_message}")
        _jobs[job_id]["status"] = JobStatus.FAILED
        _jobs[job_id]["error_message"] = error_message

    except Exception as e:
        error_message = str(e)
        print(f"[GuideWorker] job_id={job_id} 가이드 생성 실패: {error_message}")
        _jobs[job_id]["status"] = JobStatus.FAILED
        _jobs[job_id]["error_message"] = error_message


# ── Service ───────────────────────────────────────────────────────────────────


class GuideService:
    async def create_guide_job(self, req: GenerateGuideRequest) -> GenerateGuideResponse:
        job_id = str(uuid.uuid4())
        guide_id = str(uuid.uuid4())
        _jobs[job_id] = {"status": JobStatus.PENDING, "guide_id": None, "patient_id": req.patient_id}
        asyncio.create_task(
            _run_mock_worker(
                job_id,
                guide_id,
                req.guide_types,
                req.medication_names,
                req.medications,
                req.disease_codes,
                req.disease_names,
            )
        )
        return GenerateGuideResponse(job_id=job_id)

    async def get_job_status(self, job_id: str) -> GuideStatusResponse:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job을 찾을 수 없습니다.")
        return GuideStatusResponse(
            job_id=job_id,
            status=job["status"],
            guide_id=job.get("guide_id"),
        )

    async def get_guide(self, guide_id: str) -> GuideResponse:
        guide = _guides.get(guide_id)
        if not guide:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="가이드를 찾을 수 없습니다.")
        return GuideResponse(**guide)

    async def submit_feedback(self, guide_id: str, req: FeedbackRequest) -> FeedbackResponse:
        if guide_id not in _guides:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="가이드를 찾을 수 없습니다.")
        feedback_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).isoformat()
        _feedbacks.setdefault(guide_id, {})
        _feedbacks[guide_id]["feedback_id"] = feedback_id
        _feedbacks[guide_id]["created_at"] = created_at
        _feedbacks[guide_id]["is_submitted"] = True
        _feedbacks[guide_id]["data"] = req.model_dump()
        return FeedbackResponse(feedback_id=feedback_id, created_at=created_at)

    async def get_feedback_status(self, guide_id: str) -> FeedbackStatusResponse:
        if guide_id not in _guides:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="가이드를 찾을 수 없습니다.")
        fb = _feedbacks.get(guide_id, {})
        return FeedbackStatusResponse(is_submitted=fb.get("is_submitted", False))

    async def update_feedback_status(self, guide_id: str, req: UpdateFeedbackStatusRequest) -> FeedbackStatusResponse:
        if guide_id not in _guides:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="가이드를 찾을 수 없습니다.")
        _feedbacks.setdefault(guide_id, {})
        _feedbacks[guide_id]["is_submitted"] = req.status == "submitted"
        return FeedbackStatusResponse(is_submitted=_feedbacks[guide_id]["is_submitted"])

    async def get_guide_context(self, guide_id: str) -> GuideContextResponse:
        guide = _guides.get(guide_id)
        if not guide:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="가이드를 찾을 수 없습니다.")

        medications: list[str] = []
        if guide.get("medication_guide"):
            medications = [m["name"] for m in guide["medication_guide"].get("medications", [])]

        schedule: list[dict] = guide.get("schedule_table") or []

        lifestyle = guide.get("lifestyle_guide")
        tips = lifestyle.get("tips", []) if lifestyle else []
        key_instructions = tips if tips else _FALLBACK_KEY_INSTRUCTIONS

        return GuideContextResponse(
            guide_id=guide_id,
            medications=medications,
            schedule=schedule,
            key_instructions=key_instructions,
            disease_codes=guide.get("disease_codes", []),
        )
