import logging

from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import config as app_config

logger = logging.getLogger(__name__)

_EMBED_MODEL = "text-embedding-3-small"
_TOP_K = 3
_MIN_SIMILARITY = 0.7  # 코사인 유사도 임계값 (거리 기준: 1 - 0.7 = 0.3)
_openai_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=app_config.OPENAI_API_KEY)
    return _openai_client


async def search_drug_by_query(session: AsyncSession, query: str) -> list[dict]:
    """사용자 질문을 임베딩하여 drug_master에서 의미적으로 유사한 약품 정보를 반환한다."""
    try:
        resp = await _get_client().embeddings.create(model=_EMBED_MODEL, input=query)
        vec_str = "[" + ",".join(str(v) for v in resp.data[0].embedding) + "]"
    except Exception:
        logger.exception("RAG 임베딩 생성 실패")
        return []

    try:
        rows = (
            await session.execute(
                text(
                    "SELECT item_name, dosage, side_effects, cautions "
                    "FROM drug_master "
                    "WHERE embedding IS NOT NULL "
                    "  AND embedding <=> (:vec)::vector < :dist_threshold "
                    "ORDER BY embedding <=> (:vec)::vector "
                    "LIMIT :k"
                ),
                {"vec": vec_str, "k": _TOP_K, "dist_threshold": 1 - _MIN_SIMILARITY},
            )
        ).fetchall()
    except Exception:
        logger.exception("RAG 벡터 검색 실패")
        return []

    return [
        {
            "name": row.item_name,
            "dosage": row.dosage,
            "side_effects": row.side_effects,
            "cautions": row.cautions,
        }
        for row in rows
    ]
