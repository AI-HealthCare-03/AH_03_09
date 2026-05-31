import asyncio
import json
import os
import pathlib
import uuid
from datetime import UTC, datetime

# client = AsyncOpenAI(
#     api_key=os.getenv("OPENAI_API_KEY"),
# )
import pandas as pd
from fastapi import HTTPException, status
from openai import AsyncOpenAI

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
    MedicationGuide,
    MedicationItem,
    MedicationMatchStatus,
    UpdateFeedbackStatusRequest,
)

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


# ── CSV 매핑 헬퍼 ─────────────────────────────────────────────────────────────


def _safe_str(val: object) -> str:
    s = str(val).strip()
    return s if s and s.lower() != "nan" else ""


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


async def _make_easy_summary_llm(
    dosage: str,
    cautions: list[str],
    side_effects: list[str],
    storage: str,
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
                "content": (
                    "당신은 복약 정보를 환자 친화적인 한국어로 요약하는 도우미입니다.\n"
                    "반드시 아래 규칙을 따르세요:\n"
                    "- 제공된 데이터에 없는 약효, 진단, 처방 정보를 절대 추가하지 마세요.\n"
                    "- 3~5개의 독립적인 짧은 문장으로만 작성하세요.\n"
                    '- 응답은 반드시 JSON 형식으로: {"sentences": ["문장1", "문장2", ...]}'
                ),
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
    try:
        return await _make_easy_summary_llm(
            item.dosage,
            item.cautions,
            item.side_effects,
            item.storage,
        )
    except Exception:
        return item.easy_summary


def _search_medication(name: str) -> MedicationItem:
    df = _get_drug_df()
    normalized = name.strip().lower().replace(" ", "")
    mask = (
        df["itemName"]
        .astype(str)
        .str.lower()
        .str.replace(" ", "", regex=False)
        .str.contains(normalized, na=False, regex=False)
    )
    matches = df[mask]
    if matches.empty:
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


async def _make_medication_guide_from_csv(medication_names: list[str]) -> MedicationGuide:
    items = [_search_medication(n) for n in medication_names]
    enriched_summaries = await asyncio.gather(*[_enrich_easy_summary(item) for item in items])
    for item, summary in zip(items, enriched_summaries, strict=True):
        item.easy_summary = summary
    return MedicationGuide(medications=items)


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


async def _make_lifestyle_guide_with_llm(medication_names: list[str]):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = AsyncOpenAI(api_key=api_key)

    prompt = f"""
다음 약물을 복용하는 환자를 위한 생활관리 가이드를 작성해주세요.

조건:
- 한국어로 작성
- 환자가 이해하기 쉬운 표현 사용
- 생활관리 팁 4개를 줄바꿈 목록으로 작성
- 각 항목은 한 문장으로 작성
- 각 항목은 반드시 "[LLM생성]"으로 시작할 것
- 진단이나 처방처럼 단정하지 말 것

약물:
{", ".join(medication_names)}
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


async def _run_mock_worker(
    job_id: str, guide_id: str, guide_types: list[GuideType], medication_names: list[str]
) -> None:
    await asyncio.sleep(1)
    _jobs[job_id]["status"] = JobStatus.PROCESSING

    await asyncio.sleep(3)

    now = datetime.now(UTC).isoformat()

    generation_results = [GuideGenerationResult(guide_type=gt, status=GuideGenerationStatus.DONE) for gt in guide_types]

    if GuideType.LIFESTYLE in guide_types:
        try:
            lifestyle_guide = await _make_lifestyle_guide_with_llm(medication_names)
        except Exception as e:
            print(f"LLM guide generation failed: {e}")
            lifestyle_guide = _make_lifestyle_guide()
    else:
        lifestyle_guide = None

    guide = GuideResponse(
        guide_id=guide_id,
        guide_types=guide_types,
        created_at=now,
        medication_guide=(
            await _make_medication_guide_from_csv(medication_names) if GuideType.MEDICATION in guide_types else None
        ),
        schedule_table=[
            {
                "time": "아침 식후",
                "medications": ["아모잘탄"],
            },
            {
                "time": "필요 시",
                "medications": ["어린이타이레놀산160밀리그램(아세트아미노펜)"],
            },
        ],
        lifestyle_guide=lifestyle_guide,
        diet_guide=_make_diet_guide() if GuideType.DIET in guide_types else None,
        exercise_guide=_make_exercise_guide() if GuideType.EXERCISE in guide_types else None,
        generation_results=generation_results,
    )

    _guides[guide_id] = guide.model_dump()
    _jobs[job_id]["status"] = JobStatus.DONE
    _jobs[job_id]["guide_id"] = guide_id


# ── Service ───────────────────────────────────────────────────────────────────


class GuideService:
    async def create_guide_job(self, req: GenerateGuideRequest) -> GenerateGuideResponse:
        job_id = str(uuid.uuid4())
        guide_id = str(uuid.uuid4())
        _jobs[job_id] = {"status": JobStatus.PENDING, "guide_id": None, "patient_id": req.patient_id}
        asyncio.create_task(_run_mock_worker(job_id, guide_id, req.guide_types, req.medication_names))
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

        key_instructions: list[str] = []
        if guide.get("lifestyle_guide"):
            key_instructions = guide["lifestyle_guide"].get("tips", [])

        return GuideContextResponse(
            guide_id=guide_id,
            medications=medications,
            schedule=schedule,
            key_instructions=key_instructions,
            disease_codes=[],
        )
