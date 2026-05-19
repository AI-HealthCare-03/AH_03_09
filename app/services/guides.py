import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status

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
    ScheduleEntry,
    UpdateFeedbackStatusRequest,
)

# ── In-memory 저장소 ──────────────────────────────────────────────────────────
_jobs: dict[str, dict] = {}
_guides: dict[str, dict] = {}
_feedbacks: dict[str, dict] = {}


# ── Mock 데이터 생성 헬퍼 ─────────────────────────────────────────────────────


def _make_medication_guide() -> MedicationGuide:
    return MedicationGuide(
        medications=[
            MedicationItem(
                name="아목시실린 500mg",
                dosage="1정",
                timing="아침·점심·저녁 1일 3회",
                before_after_meal="식후 30분",
                side_effects=["구역질", "설사", "피부 발진"],
                cautions=["페니실린 알레르기 환자 복용 금지", "음주 자제"],
                missed_dose="생각난 즉시 복용, 다음 복용 시간이 가까우면 건너뜀",
                storage="직사광선 피해 실온 보관",
                match_status=MedicationMatchStatus.EXACT_DB_MATCH,
                source_name="식약처 의약품개요정보",
                disclaimer=None,
            ),
            MedicationItem(
                name="이부프로펜 200mg",
                dosage="1정",
                timing="아침·저녁 1일 2회",
                before_after_meal="식후",
                side_effects=["위장 장애", "두통", "어지러움"],
                cautions=["공복 복용 금지", "신장 질환자 주의"],
                missed_dose="생각난 즉시 복용, 2회분 동시 복용 금지",
                storage="습기 피해 서늘한 곳 보관",
                match_status=MedicationMatchStatus.WEB_REFERENCE,
                source_name="약학정보원",
                disclaimer="웹 참조 정보로 정확도가 낮을 수 있습니다. 복약 전 전문가와 상담하세요.",
            ),
        ]
    )


def _make_schedule_table() -> list[ScheduleEntry]:
    return [
        ScheduleEntry(time="08:00 (아침 식후)", medications=["아목시실린 500mg 1정", "이부프로펜 200mg 1정"]),
        ScheduleEntry(time="13:00 (점심 식후)", medications=["아목시실린 500mg 1정"]),
        ScheduleEntry(time="19:00 (저녁 식후)", medications=["아목시실린 500mg 1정", "이부프로펜 200mg 1정"]),
    ]


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


async def _run_mock_worker(job_id: str, guide_id: str, guide_types: list[GuideType]) -> None:
    await asyncio.sleep(1)
    _jobs[job_id]["status"] = JobStatus.PROCESSING

    await asyncio.sleep(3)

    now = datetime.now(UTC).isoformat()

    generation_results = [GuideGenerationResult(guide_type=gt, status=GuideGenerationStatus.DONE) for gt in guide_types]

    guide = GuideResponse(
        guide_id=guide_id,
        guide_types=guide_types,
        created_at=now,
        medication_guide=_make_medication_guide() if GuideType.MEDICATION in guide_types else None,
        # schedule_table은 MEDICATION 가이드 요청 시 함께 제공
        schedule_table=_make_schedule_table() if GuideType.MEDICATION in guide_types else None,
        lifestyle_guide=_make_lifestyle_guide() if GuideType.LIFESTYLE in guide_types else None,
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
        asyncio.create_task(_run_mock_worker(job_id, guide_id, req.guide_types))
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
        return GuideContextResponse(
            guide_id=guide_id,
            medications=medications,
            disease_codes=["J06.9", "M79.3"],
            key_instructions=[
                "식후 복용을 반드시 지켜주세요.",
                "음주 중 복용을 삼가세요.",
                "증상 악화 시 즉시 의사와 상담하세요.",
            ],
        )
