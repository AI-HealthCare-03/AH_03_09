import asyncio
import json
import logging
import time
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import config as app_config
from app.core.db.sqlalchemy_client import get_async_session
from app.core.redis_client import get_redis
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.drug_master import DrugMaster
from app.models.guides import Guide
from app.models.health_profiles import HealthProfile
from app.models.users import User
from app.repositories.chat_repository import ChatRepository
from app.services.guides import GuideService
from app.services.rag import search_drug_by_query

logger = logging.getLogger(__name__)

RESPONSE_TIMEOUT_SECONDS = 25
DELAY_WARNING_SECONDS = 12

_EXERCISE_MAP = {"REGULAR": "규칙적", "IRREGULAR": "비규칙적", "NONE": "안 함"}
_ALCOHOL_MAP = {"NONE": "안 함", "MODERATE": "가끔", "HEAVY": "자주"}

_DANGER_KEYWORDS = [
    "자살",
    "자해",
    "죽고 싶",
    "죽고싶",
    "죽을 것 같",
    "극단적 선택",
    "과다복용",
    "약 다 먹",
    "전부 먹으면",
    "목을 매",
    "뛰어내려",
]
_INAPPROPRIATE_KEYWORDS = [
    # 기본 욕설
    "씨발",
    "시발",
    "씨바",
    "시바",
    "씨팔",
    "시팔",
    # 개- 계열
    "개새끼",
    "개놈",
    "개년",
    "개쓰레기",
    "개소리",
    "개지랄",
    # 병신 계열
    "병신",
    "벙신",
    "찐따",
    # 성기 관련
    "좆",
    "자지",
    "보지",
    # 초성체/축약
    "ㅅㅂ",
    "ㅂㅅ",
    "ㅆㅂ",
    "ㄲㅈ",
    "ㅈㄹ",
    # 미친 계열
    "미친놈",
    "미친년",
    "미친새끼",
    # 죽어/꺼져 계열
    "뒤져",
    "꺼져",
    # 창녀 계열
    "창녀",
    "창년",
    # 비하 표현
    "지랄",
    "새끼",
    "닥쳐",
    "바보",
    "멍청이",
    # 지능 비하
    "머저리",
    "얼간이",
    "등신",
    "돌대가리",
    "저능아",
    # 강도 표현 (욕설 강조어)
    "존나",
    "졸라",
    # 인신공격
    "인간쓰레기",
    "찌질이",
    "걸레",
    # 복합 변형
    "개같",
    "좆같",
]

_DANGER_RESPONSE = (
    "지금 많이 힘드신 것 같아요. 혼자 감당하기 어려운 순간이라면 전문가의 도움을 받으시길 권합니다.\n\n"
    "📞 자살예방상담전화 109 (24시간)\n"
    "📞 정신건강위기상담전화 1577-0199 (24시간)\n\n"
    "약물과 관련된 응급 상황이라면 즉시 119에 연락하거나 가까운 응급실을 방문해 주세요.\n\n"
    "⚠️ 본 답변은 AI가 생성한 의료 정보입니다. 정확한 복약 지도는 담당 의사·약사에게 확인하시기 바랍니다."
)
_INAPPROPRIATE_RESPONSE = "죄송합니다. 해당 질문에는 답변하기 어렵습니다. 약물 복용 및 건강 관련 질문을 부탁드립니다."


def _check_content(content: str) -> str:
    """위험/부적절 키워드 여부를 반환한다. 정상이면 'ok'."""
    if any(kw in content for kw in _DANGER_KEYWORDS):
        return "danger"
    if any(kw in content for kw in _INAPPROPRIATE_KEYWORDS):
        return "inappropriate"
    return "ok"


_PRESET_RESPONSES = {
    "danger": _DANGER_RESPONSE,
    "inappropriate": _INAPPROPRIATE_RESPONSE,
}

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=app_config.OPENAI_API_KEY)
    return _openai_client


async def _generate_title(content: str) -> str:
    try:
        resp = await _get_openai_client().chat.completions.create(
            model=app_config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "사용자 메시지를 보고 대화 제목을 한국어로 15자 이내로 만들어라. 제목만 반환하고 따옴표나 설명은 붙이지 마라.",
                },
                {"role": "user", "content": content},
            ],
            max_tokens=30,
            temperature=0.3,
        )
        title = (resp.choices[0].message.content or "").strip()
        return title[:20] if title else "새 대화"
    except Exception:
        logger.warning("[title_gen] 제목 생성 실패")
        return "새 대화"


class ChatService:
    def __init__(self, session: Annotated[AsyncSession, Depends(get_async_session)]) -> None:
        self.session = session
        self.repo = ChatRepository(session)

    async def update_message_feedback(
        self, session_id: UUID | str, message_id: int, user_id: int, feedback: str
    ) -> ChatMessage:
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
        msg = await self.repo.update_message_feedback(message_id, session_id, feedback)
        if not msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="메시지를 찾을 수 없습니다.")
        return msg

    async def get_session_detail(self, session_id: UUID | str, user_id: int) -> tuple[ChatSession, list] | None:
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            return None
        messages = await self.repo.get_messages(session_id)
        return session, messages

    async def delete_session(self, session_id: UUID | str, user_id: int) -> None:
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
        await self.repo.delete_session(session_id)

    async def _fetch_health_context(self, user_id: int) -> dict | None:
        health_result = await self.session.execute(select(HealthProfile).where(HealthProfile.user_id == user_id))
        health_profile = health_result.scalar_one_or_none()

        user_result = await self.session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not health_profile and not user:
            return None

        ctx: dict = {}

        if user:
            ctx["gender"] = user.gender
            ctx["age_range"] = user.age_range
            ctx["birthday"] = user.birthday
            ctx["birthyear"] = user.birthyear

        if health_profile:
            ctx.update(
                {
                    "height_cm": health_profile.height_cm,
                    "weight_kg": health_profile.weight_kg,
                    "blood_pressure_systolic": health_profile.blood_pressure_systolic,
                    "blood_pressure_diastolic": health_profile.blood_pressure_diastolic,
                    "primary_conditions": health_profile.primary_conditions,
                    "allergies": health_profile.allergies,
                    "current_medications": health_profile.current_medications,
                    "lifestyle_exercise": _EXERCISE_MAP.get(health_profile.lifestyle_exercise, "안 함"),
                    "lifestyle_smoking": health_profile.lifestyle_smoking,
                    "lifestyle_alcohol": _ALCOHOL_MAP.get(health_profile.lifestyle_alcohol, "안 함"),
                }
            )

        return ctx

    async def _fetch_drug_details(self, medication_names: list[str]) -> list[dict]:
        """처방 약품명으로 drug_master 조회해 상세 정보(용법·부작용·주의사항) 반환."""
        if not medication_names:
            return []
        details: list[dict] = []
        for name in medication_names:
            result = await self.session.execute(
                select(DrugMaster).where(DrugMaster.item_name.ilike(f"%{name}%")).limit(1)
            )
            drug = result.scalar_one_or_none()
            if drug:
                details.append(
                    {
                        "name": name,
                        "dosage": drug.dosage,
                        "side_effects": drug.side_effects,
                        "cautions": drug.cautions,
                    }
                )
        return details

    async def _get_guide_context(self, guide_id: str | None) -> dict | None:
        if not guide_id:
            logger.info("[guide_context] guide_id 없음 → None 반환")
            return None
        try:
            ctx = await GuideService().get_guide_context(guide_id)
            result = {
                "medications": ctx.medications,
                "schedule": ctx.schedule,
                "key_instructions": ctx.key_instructions,
                "disease_codes": ctx.disease_codes,
                "disease_names": ctx.disease_names,
                "drug_details": ctx.drug_details,
            }
            logger.info("[guide_context] 조회 성공 guide_id=%s medications=%s", guide_id, ctx.medications)
            return result
        except HTTPException as e:
            logger.warning("[guide_context] 조회 실패 guide_id=%s detail=%s", guide_id, e.detail)
            return None

    async def _get_all_user_guide_contexts(self, user_id: int) -> list[dict]:
        """유저의 모든 가이드를 최신순으로 가져와 레이블이 붙은 컨텍스트 목록을 반환한다."""
        result = await self.session.execute(
            select(Guide).where(Guide.patient_id == str(user_id)).order_by(Guide.created_at.asc()).limit(7)
        )
        rows = result.scalars().all()
        guides: list[dict] = []
        for idx, row in enumerate(rows, start=1):
            data = row.guide_data or {}
            medications: list[str] = []
            drug_details: list[dict] = []
            if data.get("medication_guide"):
                for m in data["medication_guide"].get("medications", []):
                    name = m.get("name")
                    if not name:
                        continue
                    medications.append(name)
                    se = m.get("side_effects", [])
                    ca = m.get("cautions", [])
                    drug_details.append(
                        {
                            "name": name,
                            "dosage": m.get("dosage") or "",
                            "side_effects": ", ".join(se) if isinstance(se, list) else (se or ""),
                            "cautions": ", ".join(ca) if isinstance(ca, list) else (ca or ""),
                        }
                    )
            if not medications:
                medications = [n for n in (data.get("medication_names") or []) if n]
            codes = data.get("disease_codes") or []
            names = data.get("disease_names") or []
            disease_pairs = [(codes[i], names[i] if i < len(names) else "") for i in range(len(codes))]
            lifestyle = data.get("lifestyle_guide")
            tips = lifestyle.get("tips", []) if lifestyle else []
            guides.append(
                {
                    "label": f"가이드 {idx}",
                    "created_at": row.created_at.strftime("%Y-%m-%d") if row.created_at else "",
                    "medications": medications,
                    "schedule": data.get("schedule_table") or [],
                    "key_instructions": tips,
                    "disease_codes": [p[0] for p in disease_pairs],
                    "disease_names": [p[1] for p in disease_pairs],
                    "drug_details": drug_details,
                }
            )
        return guides

    async def _resolve_drug_context(self, guides: list[dict], content: str) -> tuple[list[dict], list[dict]]:
        """전체 가이드 약품 데이터 + RAG 병행 실행. 가이드 약품은 RAG 결과에서 제거."""
        guide_drug_details: list[dict] = []
        for g in guides:
            guide_drug_details.extend(g.get("drug_details") or [])

        if not guide_drug_details:
            all_meds = [m for g in guides for m in (g.get("medications") or [])]
            guide_drug_details = await self._fetch_drug_details(all_meds)

        rag_results = await search_drug_by_query(self.session, content)
        if guide_drug_details and rag_results:
            guide_names = {d["name"].lower() for d in guide_drug_details}
            rag_results = [
                r
                for r in rag_results
                if not any(gn in r["name"].lower() or r["name"].lower() in gn for gn in guide_names)
            ]
        return guide_drug_details, rag_results

    async def stream_message(self, session_id: UUID | str, user_id: int, content: str, guide_id: str | None = None):  # noqa: C901
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            yield json.dumps({"type": "error", "detail": "세션을 찾을 수 없습니다."}) + "\n"
            return

        preset = _PRESET_RESPONSES.get(_check_content(content))
        if preset:
            await self.repo.create_message(session_id, MessageRole.USER, content)
            await self.repo.create_message(session_id, MessageRole.ASSISTANT, preset)
            yield json.dumps({"type": "chunk", "chunk": preset}) + "\n"
            yield json.dumps({"type": "done", "content": preset}) + "\n"
            return

        await self.repo.create_message(session_id, MessageRole.USER, content)

        history = await self.repo.get_messages(session_id, limit=20)
        is_first_message = len(history) == 1
        history_payload = [{"role": m.role, "content": m.content} for m in history[:-1]]

        health_context = await self._fetch_health_context(user_id)
        if guide_id:
            guide_ctx = await self._get_guide_context(guide_id)
            guides = (
                [
                    {
                        "label": "선택된 가이드",
                        "medications": guide_ctx["medications"],
                        "schedule": guide_ctx["schedule"],
                        "key_instructions": guide_ctx["key_instructions"],
                        "disease_codes": guide_ctx["disease_codes"],
                        "disease_names": guide_ctx["disease_names"],
                        "drug_details": guide_ctx["drug_details"],
                    }
                ]
                if guide_ctx
                else []
            )
        else:
            guides = await self._get_all_user_guide_contexts(user_id)
        drug_details, rag_results = await self._resolve_drug_context(guides, content)

        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"chat:stream:{session_id}")

        task_payload = json.dumps(
            {
                "session_id": str(session_id),
                "user_message": content,
                "history": history_payload,
                "health_profile": health_context,
                "guides": guides or None,
                "drug_details": drug_details or None,
                "rag_results": rag_results or None,
            }
        )
        await redis.publish(f"chat:request:{session_id}", task_payload)

        full_response: list[str] = []
        start_time = time.monotonic()
        delay_sent = False
        try:
            async with asyncio.timeout(RESPONSE_TIMEOUT_SECONDS):
                async for redis_msg in pubsub.listen():
                    if not delay_sent and not full_response and (time.monotonic() - start_time) > DELAY_WARNING_SECONDS:
                        yield (
                            json.dumps(
                                {"type": "delay", "detail": "조금만 더 기다려주세요. AI가 답변을 준비하고 있습니다."}
                            )
                            + "\n"
                        )
                        delay_sent = True
                    if redis_msg["type"] != "message":
                        continue
                    data: str = redis_msg["data"]
                    if data.startswith("[ERROR]"):
                        yield json.dumps({"type": "error", "detail": data[7:]}) + "\n"
                        return
                    if data == "[DONE]":
                        break
                    full_response.append(data)
                    yield json.dumps({"type": "chunk", "chunk": data}) + "\n"
        except TimeoutError:
            yield json.dumps({"type": "error", "detail": "AI 응답 시간 초과. 다시 시도해 주세요."}) + "\n"
            return
        finally:
            await pubsub.unsubscribe(f"chat:stream:{session_id}")
            await pubsub.aclose()

        complete = "".join(full_response)
        if complete:
            await self.repo.create_message(session_id, MessageRole.ASSISTANT, complete)
            await self.repo.touch_session(session_id)

        if is_first_message and complete:
            title = await _generate_title(content)
            await self.repo.update_title(session_id, title)
            yield json.dumps({"type": "title", "title": title}) + "\n"

        if not guides:
            yield json.dumps({"type": "action", "action": "guide_prompt"}) + "\n"
        yield json.dumps({"type": "done", "content": complete}) + "\n"

    async def create_session(self, user_id: int, title: str = "새 대화") -> ChatSession:
        return await self.repo.create_session(user_id, title)

    async def get_user_sessions(self, user_id: int) -> list[ChatSession]:
        return await self.repo.get_sessions(user_id)

    async def get_session_messages(self, session_id: UUID | str, user_id: int) -> list | None:
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            return None
        return await self.repo.get_messages(session_id)

    async def _collect_redis_stream(self, session_id: UUID | str) -> tuple[str, str | None]:
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"chat:stream:{session_id}")

        full_response: list[str] = []
        error_detail: str | None = None
        try:
            async with asyncio.timeout(RESPONSE_TIMEOUT_SECONDS):
                async for redis_msg in pubsub.listen():
                    if redis_msg["type"] != "message":
                        continue
                    data: str = redis_msg["data"]
                    if data.startswith("[ERROR]"):
                        error_detail = data[7:]
                        break
                    if data == "[DONE]":
                        break
                    full_response.append(data)
        except TimeoutError:
            error_detail = "AI 응답 시간 초과"
        finally:
            await pubsub.unsubscribe(f"chat:stream:{session_id}")
            await pubsub.aclose()

        return "".join(full_response), error_detail

    async def send_message_sync(
        self, session_id: UUID | str, user_id: int, content: str, guide_id: str | None = None
    ) -> tuple[ChatMessage, ChatMessage]:
        """Swagger 테스트용 REST 래퍼: WebSocket과 동일한 흐름이지만 모든 스트림을 모아 한 번에 반환."""
        session = await self.repo.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")

        preset = _PRESET_RESPONSES.get(_check_content(content))
        if preset:
            user_msg = await self.repo.create_message(session_id, MessageRole.USER, content)
            assistant_msg = await self.repo.create_message(session_id, MessageRole.ASSISTANT, preset)
            return user_msg, assistant_msg

        user_msg = await self.repo.create_message(session_id, MessageRole.USER, content)

        history = await self.repo.get_messages(session_id, limit=20)
        is_first_message = len(history) == 1
        history_payload = [{"role": m.role, "content": m.content} for m in history[:-1]]

        health_context = await self._fetch_health_context(user_id)
        guides = await self._get_all_user_guide_contexts(user_id)
        drug_details, rag_results = await self._resolve_drug_context(guides, content)

        redis = await get_redis()
        task_payload = json.dumps(
            {
                "session_id": str(session_id),
                "user_message": content,
                "history": history_payload,
                "health_profile": health_context,
                "guides": guides or None,
                "drug_details": drug_details or None,
                "rag_results": rag_results or None,
            }
        )
        await redis.publish(f"chat:request:{session_id}", task_payload)

        complete, error_detail = await self._collect_redis_stream(session_id)

        if error_detail:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI 응답 실패: {error_detail}")

        if not complete:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI 응답 실패: 빈 응답")
        assistant_msg = await self.repo.create_message(session_id, MessageRole.ASSISTANT, complete)
        await self.repo.touch_session(session_id)
        if is_first_message:
            title = await _generate_title(content)
            await self.repo.update_title(session_id, title)
        return user_msg, assistant_msg
