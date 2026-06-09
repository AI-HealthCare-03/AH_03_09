"""
가이드 생성 Worker — app.* import 없이 asyncpg + aioredis + OpenAI 기반으로 동작.
참조: app/services/guides.py (_run_mock_worker, _fetch_health_profile_for_guide, _persist_guide)
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import UTC, datetime

import asyncpg
import redis.asyncio as aioredis
from openai import AsyncOpenAI

from ai_worker.core.config import config
from ai_worker.core.logger import setup_logger
from ai_worker.schemas.guide import GuideJobPayload

logger = setup_logger("ai_worker.guide_task")

# ── Redis Job 관리 (app/services/guides.py와 동일한 키 패턴) ────────────────
_JOB_TTL = 86400  # 24h


async def _get_job(redis: aioredis.Redis, job_id: str) -> dict | None:
    raw = await redis.get(f"guide:job:{job_id}")
    return json.loads(raw) if raw else None


async def _update_job(redis: aioredis.Redis, job_id: str, **updates: object) -> None:
    job = await _get_job(redis, job_id) or {}
    job.update(updates)
    await redis.set(f"guide:job:{job_id}", json.dumps(job, ensure_ascii=False), ex=_JOB_TTL)


# ── 순수 함수 (guides.py에서 복사) ────────────────────────────────────────────

_HP_EXERCISE_LABEL: dict[str, str] = {
    "REGULAR": "규칙적 (주 3회 이상)",
    "IRREGULAR": "비규칙적",
    "NONE": "",
}
_HP_ALCOHOL_LABEL: dict[str, str] = {
    "NONE": "",
    "MODERATE": "가끔 (주 1~2회)",
    "HEAVY": "자주 (주 3회 이상)",
}


def _normalize_drug_name(name: str) -> str:
    n = name.strip().lower().replace(" ", "")
    n = re.sub(r"(\d)mg\b", r"\1밀리그램", n, flags=re.IGNORECASE)
    n = re.sub(r"(\d)mcg\b", r"\1마이크로그램", n, flags=re.IGNORECASE)
    n = re.sub(r"(\d)ml\b", r"\1밀리리터", n, flags=re.IGNORECASE)
    n = re.sub(r"[캡캅]셀", "캡슐", n)
    return n


def _build_health_profile_section(health_profile: dict | None) -> str:
    if not health_profile:
        return ""
    parts: list[str] = []
    conditions = health_profile.get("primary_conditions") or []
    if conditions:
        parts.append(f"기저질환: {', '.join(str(c) for c in conditions)}")
    allergies = health_profile.get("allergies") or []
    if allergies:
        parts.append(f"알레르기: {', '.join(str(a) for a in allergies)}")
    bp_sys = health_profile.get("blood_pressure_systolic")
    bp_dia = health_profile.get("blood_pressure_diastolic")
    if bp_sys and bp_dia:
        parts.append(f"혈압: {bp_sys}/{bp_dia} mmHg")
    lifestyle: list[str] = []
    exercise = _HP_EXERCISE_LABEL.get(health_profile.get("lifestyle_exercise") or "NONE", "")
    if exercise:
        lifestyle.append(f"운동 {exercise}")
    if health_profile.get("lifestyle_smoking"):
        lifestyle.append("흡연 중")
    alcohol = _HP_ALCOHOL_LABEL.get(health_profile.get("lifestyle_alcohol") or "NONE", "")
    if alcohol:
        lifestyle.append(f"음주 {alcohol}")
    if lifestyle:
        parts.append(f"생활습관: {', '.join(lifestyle)}")
    if not parts:
        return ""
    return (
        "\n환자 건강 정보 (가이드 작성 시 참고할 정보."
        " 확정 진단 정보는 아니며 진단·치료·처방 판단에는 사용하지 말 것):\n" + "\n".join(f"- {p}" for p in parts)
    )


def _build_schedule_table(medications: list[dict]) -> list[dict]:
    """payload.medications (dict 리스트)에서 시간대별 복용 일정 생성."""
    schedule: dict[str, list[str]] = {}
    for med in medications:
        name = med.get("medication_name", "")
        timing = med.get("timing") or ""
        time_of_day = med.get("time_of_day") or []
        if timing:
            schedule.setdefault(timing, []).append(name)
        elif time_of_day:
            for slot in time_of_day:
                schedule.setdefault(str(slot), []).append(name)
        else:
            schedule.setdefault("처방전/약봉투 안내 참고", []).append(name)
    return [{"time": t, "medications": names} for t, names in schedule.items()]


# ── Fallback 가이드 (LLM 실패 시) ────────────────────────────────────────────
_FALLBACK_LIFESTYLE_TIPS = [
    "하루 7~8시간 충분한 수면을 취하세요.",
    "스트레스를 줄이고 규칙적인 생활 패턴을 유지하세요.",
    "금연·금주를 권장합니다.",
    "복약 중 졸음이 올 수 있으니 운전 및 기계 조작 시 주의하세요.",
]
_FALLBACK_DIET: dict[str, object] = {
    "forbidden": ["알코올", "자몽 주스", "고지방 음식"],
    "recommended": ["통곡물", "채소류", "저지방 단백질 (닭가슴살, 두부)"],
    "hydration": "하루 1.5~2L 물 섭취를 권장합니다.",
}
_FALLBACK_EXERCISE: dict[str, object] = {
    "intensity": "저강도 (가벼운 걷기·스트레칭)",
    "frequency": "주 3~5회",
    "duration": "1회 20~30분",
    "cautions": [
        "복약 후 어지러움이 있을 경우 즉시 운동 중단",
        "통증 발생 시 휴식 우선",
        "격렬한 유산소 운동은 증상 완화 후 재개",
    ],
}


# ── DB 조회 (asyncpg) ─────────────────────────────────────────────────────────


async def _fetch_health_profile(conn: asyncpg.Connection, patient_id_str: str | None) -> dict | None:
    try:
        pid = int(patient_id_str or "")
    except (ValueError, TypeError):
        return None
    try:
        row = await conn.fetchrow(
            "SELECT primary_conditions, allergies, blood_pressure_systolic, "
            "blood_pressure_diastolic, lifestyle_exercise, lifestyle_smoking, "
            "lifestyle_alcohol FROM health_profiles WHERE user_id = $1",
            pid,
        )
        return dict(row) if row is not None else None
    except Exception:
        logger.exception("health_profile 조회 실패 patient_id=%s", patient_id_str)
        return None


async def _search_medication_db(conn: asyncpg.Connection, name: str) -> dict | None:
    normalized = _normalize_drug_name(name)
    try:
        row = await conn.fetchrow(
            "SELECT item_name, dosage, cautions, side_effects, storage, etc_otc_code, source "
            "FROM drug_master "
            "WHERE word_similarity($1, item_name) > 0.6 "
            "ORDER BY word_similarity($1, item_name) DESC LIMIT 1",
            normalized,
        )
        return dict(row) if row is not None else None
    except Exception:
        logger.exception("drug_master 조회 실패 name=%s", name)
        return None


async def _persist_guide(
    conn: asyncpg.Connection,
    guide_id: str,
    patient_id: str | None,
    guide_data: dict,
) -> None:
    await conn.execute(
        "INSERT INTO guides (guide_id, patient_id, guide_data, created_at, updated_at) "
        "VALUES ($1, $2, $3::jsonb, NOW(), NOW())",
        guide_id,
        patient_id,
        json.dumps(guide_data, ensure_ascii=False),
    )


# ── LLM easy_summary 보강 (app/services/guides.py에서 복사) ──────────────────

_DEFAULT_SUMMARY_PROMPT = (
    "당신은 복약 정보를 환자 친화적인 한국어로 요약하는 도우미입니다.\n"
    "반드시 아래 규칙을 따르세요:\n"
    "- 제공된 데이터에 용도 또는 적응증이 명확히 있을 때만 첫 번째 문장에 이 약의 주요 용도를 환자가 이해하기 쉬운 말로 한 문장으로 설명하세요.\n"
    "  불분명하면 용도를 추론하지 말고, 복약 주의사항 중심으로 작성하세요.\n"
    "- 용량(mg 등 수치), 복용 횟수(1일 n회), 복용 기간(n주·n개월), 병용요법 용량 등 구체적인 투여 수치는 새로 요약하거나 서술하지 마세요.\n"
    "- 복용 방법은 구체적인 수치 대신 '처방받은 방법을 지켜 복용하세요' 수준으로 일반화하세요.\n"
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
    "- 제공된 데이터에 용도 또는 적응증이 명확히 있을 때만 첫 번째 문장에 이 약의 주요 용도를 환자가 이해하기 쉬운 말로 한 문장으로 설명하세요.\n"
    "  불분명하면 용도를 추론하지 말고, 복약 주의사항 중심으로 작성하세요.\n"
    "- 용량(mg 등 수치), 복용 횟수(1일 n회), 복용 기간(n주·n개월), 병용요법 용량 등 구체적인 투여 수치는 새로 요약하거나 서술하지 마세요.\n"
    "- 복용 방법은 구체적인 수치 대신 '처방받은 방법을 지켜 복용하세요' 수준으로 일반화하세요.\n"
    "- 이미 처방받은 환자 대상이므로, 처방 여부나 용량을 다시 결정하는 표현은 절대 사용하지 마세요.\n"
    "- 복용 중 주의사항과 실제 복약 행동 중심으로 설명하세요.\n"
    "- 식사 관계, 임신/수유 주의, 간·신장 주의, 어린이 사용 주의를 우선 포함하세요.\n"
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
    "  * 구체적인 용량 수치(mg, 1일 n회, n주 등)\n"
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

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
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


async def _enrich_easy_summary_for_dict(med: dict) -> list[str]:
    """dict 기반 medication item의 easy_summary를 LLM으로 보강. guides.py:_enrich_easy_summary 이식."""
    fallback: list[str] = med.get("easy_summary") or []
    if med.get("match_status") == "NOT_FOUND":
        return fallback
    if not config.OPENAI_API_KEY:
        return fallback
    is_web_ref = med.get("match_status") == "WEB_REFERENCE"
    prompt = _PATIENT_SUMMARY_PROMPT if is_web_ref else _DEFAULT_SUMMARY_PROMPT
    try:
        result = await _make_easy_summary_llm(
            med.get("dosage") or "",
            med.get("cautions") or [],
            med.get("side_effects") or [],
            med.get("storage") or "",
            system_prompt=prompt,
        )
        if is_web_ref:
            result = _filter_patient_summary(result)
        return result if result else fallback
    except Exception:
        return fallback


# ── Medication 아이콘/요약 생성 (app/services/guides.py에서 복사) ──────────────


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


# ── Medication Guide 구성 ─────────────────────────────────────────────────────


async def _build_medication_guide(conn: asyncpg.Connection, medication_names: list[str]) -> dict:
    medications = []
    for name in medication_names:
        row = await _search_medication_db(conn, name)
        if row:
            cautions_str = row.get("cautions") or ""
            if len(cautions_str) > 1500:
                cautions_str = cautions_str[:1500] + "... (제품허가정보 원문 일부)"
            side_effects_str = row.get("side_effects") or ""
            dosage_str = row.get("dosage") or ""
            storage_str = row.get("storage") or ""
            source = row.get("source") or "DB"
            cautions_list = [cautions_str] if cautions_str else []
            side_effects_list = [side_effects_str] if side_effects_str else []
            medications.append(
                {
                    "name": row.get("item_name", name),
                    "dosage": dosage_str,
                    "timing": "",
                    "before_after_meal": "",
                    "side_effects": side_effects_list,
                    "cautions": cautions_list,
                    "easy_summary": _make_easy_summary(cautions_list, side_effects_str, dosage_str, storage_str),
                    "missed_dose": "",
                    "storage": storage_str,
                    "action_icons": _make_medication_action_icons(cautions_list, side_effects_list, storage_str),
                    "usage_icons": _make_medication_usage_icons(dosage_str),
                    "match_status": "EXACT_DB_MATCH" if source == "식약처" else "WEB_REFERENCE",
                    "source_name": source,
                    "disclaimer": None,
                }
            )
        else:
            medications.append(
                {
                    "name": name,
                    "dosage": "",
                    "timing": "",
                    "before_after_meal": "",
                    "side_effects": [],
                    "cautions": [],
                    "easy_summary": [],
                    "missed_dose": "",
                    "storage": "",
                    "action_icons": [],
                    "usage_icons": [],
                    "match_status": "NOT_FOUND",
                    "source_name": None,
                    "disclaimer": "해당 의약품 정보를 데이터베이스에서 찾을 수 없습니다.",
                }
            )
    enriched = await asyncio.gather(*[_enrich_easy_summary_for_dict(m) for m in medications])
    for med, summary in zip(medications, enriched, strict=True):
        med["easy_summary"] = summary
    return {"medications": medications}


# ── LLM 가이드 생성 (guides.py와 동일한 프롬프트) ─────────────────────────────


def _disease_entries(disease_codes: list[str], disease_names: list[str]) -> list[str]:
    if disease_names:
        return [f"{code} - {name}" if name else code for code, name in zip(disease_codes, disease_names, strict=False)]
    return disease_codes


async def _make_lifestyle_guide(
    medication_names: list[str],
    disease_codes: list[str],
    disease_names: list[str],
    health_profile: dict | None = None,
) -> dict:
    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    entries = _disease_entries(disease_codes, disease_names)
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
- 질병분류기호는 OCR로 추출된 참고정보이며 확정 진단이 아닙니다. 확정 진단으로 표현하거나 치료·처방·수술 수준의 안내는 절대 포함하지 말 것
- 질병코드에 근거해 새로운 진단명이나 치료 지시를 생성하지 말 것
- 약물명과 질병 정보를 함께 고려하되, 환자에게 안전한 생활관리 수준으로만 작성할 것
- 환자 건강 정보(기저질환, 혈압, 알레르기, 생활습관)가 제공된 경우 생활관리 팁에 반영할 것
- 단, 확정 진단·치료 계획·처방 변경·수술 권고 등 의료적 판단은 생성하지 말 것

약물:
{", ".join(medication_names) if medication_names else "정보 없음"}

질병 정보 (OCR 추출 참고정보):
{", ".join(entries) if entries else "정보 없음"}
{_build_health_profile_section(health_profile)}
"""
    response = await client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "당신은 환자 친화적인 복약 생활관리 가이드를 작성하는 의료 AI입니다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
    )
    content = response.choices[0].message.content or ""
    tips = [line.strip("-•1234567890. ").strip() for line in content.splitlines() if line.strip()]
    return {"tips": tips if tips else _FALLBACK_LIFESTYLE_TIPS}


async def _make_diet_guide(
    medication_names: list[str],
    disease_codes: list[str],
    disease_names: list[str],
    health_profile: dict | None = None,
) -> dict:
    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    entries = _disease_entries(disease_codes, disease_names)
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
- 질병코드는 OCR 추출 참고정보이며 확정 진단이 아닙니다. 치료·처방·수술 수준의 안내는 절대 포함하지 말 것
- 안전한 생활관리 수준으로만 작성
- 환자 건강 정보(기저질환, 혈압, 알레르기, 생활습관)가 제공된 경우 식사 가이드에 반영할 것
- 단, 확정 진단·치료 계획·처방 변경·수술 권고 등 의료적 판단은 생성하지 말 것

약물:
{", ".join(medication_names) if medication_names else "정보 없음"}

질병 정보 (OCR 추출 참고정보):
{", ".join(entries) if entries else "정보 없음"}
{_build_health_profile_section(health_profile)}
"""
    response = await client.chat.completions.create(
        model=config.OPENAI_MODEL,
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
    return {
        "forbidden": forbidden if isinstance(forbidden, list) and forbidden else _FALLBACK_DIET["forbidden"],
        "recommended": recommended if isinstance(recommended, list) and recommended else _FALLBACK_DIET["recommended"],
        "hydration": hydration if isinstance(hydration, str) and hydration.strip() else _FALLBACK_DIET["hydration"],
    }


async def _make_exercise_guide(
    medication_names: list[str],
    disease_codes: list[str],
    disease_names: list[str],
    health_profile: dict | None = None,
) -> dict:
    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    entries = _disease_entries(disease_codes, disease_names)
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
- 질병코드는 OCR 추출 참고정보이며 확정 진단이 아닙니다. 치료·처방·수술 수준의 안내는 절대 포함하지 말 것
- 재활치료, 전문 운동처방 수준의 구체적인 지시는 하지 말 것
- 일반적인 생활관리 수준의 운동 가이드만 작성할 것
- 환자 건강 정보(기저질환, 혈압, 알레르기, 생활습관)가 제공된 경우 운동 가이드에 반영할 것
- 단, 확정 진단·치료 계획·처방 변경·수술 권고 등 의료적 판단은 생성하지 말 것

약물:
{", ".join(medication_names) if medication_names else "정보 없음"}

질병 정보 (OCR 추출 참고정보):
{", ".join(entries) if entries else "정보 없음"}
{_build_health_profile_section(health_profile)}
"""
    response = await client.chat.completions.create(
        model=config.OPENAI_MODEL,
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
    return {
        "intensity": intensity if isinstance(intensity, str) and intensity.strip() else _FALLBACK_EXERCISE["intensity"],
        "frequency": frequency if isinstance(frequency, str) and frequency.strip() else _FALLBACK_EXERCISE["frequency"],
        "duration": duration if isinstance(duration, str) and duration.strip() else _FALLBACK_EXERCISE["duration"],
        "cautions": cautions if isinstance(cautions, list) and cautions else _FALLBACK_EXERCISE["cautions"],
    }


# ── 가이드 섹션 생성 (복잡도 분리용) ─────────────────────────────────────────


async def _generate_guide_sections(
    conn: asyncpg.Connection,
    payload: GuideJobPayload,
    health_profile: dict | None,
    job_id: str,
) -> tuple[dict | None, dict | None, dict | None, dict | None]:
    """guide_types별 LLM/DB 가이드 섹션 생성. (lifestyle, diet, exercise, medication)"""
    lifestyle_guide: dict | None = None
    if "LIFESTYLE" in payload.guide_types:
        try:
            lifestyle_guide = await _make_lifestyle_guide(
                payload.medication_names, payload.disease_codes, payload.disease_names, health_profile
            )
        except Exception:
            logger.exception("lifestyle guide LLM 실패 job_id=%s", job_id)
            lifestyle_guide = {"tips": _FALLBACK_LIFESTYLE_TIPS}

    diet_guide: dict | None = None
    if "DIET" in payload.guide_types:
        try:
            diet_guide = await _make_diet_guide(
                payload.medication_names, payload.disease_codes, payload.disease_names, health_profile
            )
        except Exception:
            logger.exception("diet guide LLM 실패 job_id=%s", job_id)
            diet_guide = dict(_FALLBACK_DIET)

    exercise_guide: dict | None = None
    if "EXERCISE" in payload.guide_types:
        try:
            exercise_guide = await _make_exercise_guide(
                payload.medication_names, payload.disease_codes, payload.disease_names, health_profile
            )
        except Exception:
            logger.exception("exercise guide LLM 실패 job_id=%s", job_id)
            exercise_guide = dict(_FALLBACK_EXERCISE)

    medication_guide: dict | None = None
    if "MEDICATION" in payload.guide_types:
        medication_guide = await _build_medication_guide(conn, payload.medication_names)

    return lifestyle_guide, diet_guide, exercise_guide, medication_guide


def _make_schedule_table(payload: GuideJobPayload) -> list[dict] | None:
    if payload.medications:
        return _build_schedule_table(payload.medications)
    if payload.medication_names:
        return [{"time": "처방전/약봉투 안내 참고", "medications": payload.medication_names}]
    return None


# ── 메인 엔트리포인트 ──────────────────────────────────────────────────────────


async def process_guide_task(payload: GuideJobPayload) -> None:
    """
    가이드 생성 Worker.
    Redis: PENDING → PROCESSING → DONE (guide_id 포함) / FAILED (error_message 포함)
    참조: app/services/guides.py:_run_mock_worker
    """
    redis: aioredis.Redis = aioredis.from_url(config.REDIS_URL, decode_responses=True)
    conn: asyncpg.Connection | None = None

    try:
        conn = await asyncpg.connect(config.DATABASE_URL)
        await _update_job(redis, payload.job_id, status="PROCESSING")
        logger.info("guide_task START job_id=%s guide_types=%s", payload.job_id, payload.guide_types)

        guide_id = payload.guide_id or str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        health_profile = await _fetch_health_profile(conn, payload.patient_id)

        lifestyle_guide, diet_guide, exercise_guide, medication_guide = await _generate_guide_sections(
            conn, payload, health_profile, payload.job_id
        )

        guide_data: dict = {
            "guide_id": guide_id,
            "guide_types": payload.guide_types,
            "created_at": now,
            "medication_guide": medication_guide,
            "schedule_table": _make_schedule_table(payload),
            "lifestyle_guide": lifestyle_guide,
            "diet_guide": diet_guide,
            "exercise_guide": exercise_guide,
            "generation_results": [
                {"guide_type": gt, "status": "DONE", "skip_reason": None} for gt in payload.guide_types
            ],
            "disease_codes": payload.disease_codes,
            "disease_names": payload.disease_names,
        }

        await _persist_guide(conn, guide_id, payload.patient_id, guide_data)

        await _update_job(redis, payload.job_id, status="DONE", guide_id=guide_id)
        logger.info("guide_task DONE job_id=%s guide_id=%s", payload.job_id, guide_id)

    except Exception as exc:
        err_msg = str(exc)
        logger.error("guide_task FAILED job_id=%s: %s", payload.job_id, err_msg)
        try:
            await _update_job(redis, payload.job_id, status="FAILED", error_message=err_msg)
        except Exception:
            logger.exception("Redis FAILED 업데이트 실패 job_id=%s", payload.job_id)
    finally:
        if conn is not None:
            await conn.close()
        await redis.aclose()
