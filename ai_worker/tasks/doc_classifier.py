import logging
import re

from openai import AsyncOpenAI

from ai_worker.core.config import config

logger = logging.getLogger(__name__)

# 처방전 특징 키워드
_PRESCRIPTION_KW = [
    "처방전",
    "처방일",
    "처방의",
    "진료과",
    "질병분류코드",
    "질병코드",
    "상병명",
    "의료기관",
    "면허번호",
    "처방전발급",
]

# 약봉투 특징 키워드
_MEDICATION_BAG_KW = [
    "복용법",
    "용법",
    "용량",
    "복약",
    "조제",
    "약국",
    "1일",
    "식후",
    "식전",
    "식간",
    "조제일",
    "조제약사",
]

_MIN_SCORE = 1  # 규칙 분류 인정 최소 점수


def _rule_classify(text: str) -> str | None:
    """키워드 점수 기반 분류. 명확하지 않으면 None 반환."""
    normalized = re.sub(r"\s+", "", text)
    p_score = sum(1 for kw in _PRESCRIPTION_KW if kw in normalized)
    m_score = sum(1 for kw in _MEDICATION_BAG_KW if kw in normalized)

    if p_score == m_score:
        return None  # 동점 → AI로 넘김
    if p_score > m_score and p_score >= _MIN_SCORE:
        return "PRESCRIPTION"
    if m_score > p_score and m_score >= _MIN_SCORE:
        return "DRUG_BAG"
    return None


async def _ai_classify(text: str) -> str:
    """GPT를 이용한 문서 분류 (규칙 기반이 OTHER일 때만 호출)."""
    if not config.OPENAI_API_KEY:
        return "OTHER"

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "아래 텍스트가 한국 의료 문서 중 어느 종류인지 판별하세요.\n"
                        "처방전이면 PRESCRIPTION, 약봉투이면 DRUG_BAG, "
                        "판단 불가이면 OTHER 중 하나만 대문자로 답하세요."
                    ),
                },
                {"role": "user", "content": text[:600]},
            ],
            max_tokens=10,
            temperature=0,
        )
        result = resp.choices[0].message.content.strip().upper()
        if "PRESCRIPTION" in result:
            return "PRESCRIPTION"
        if "DRUG_BAG" in result or "DRUG" in result:
            return "DRUG_BAG"
    except Exception as exc:
        logger.warning("AI 문서 분류 실패, OTHER 처리: %s", exc)

    return "OTHER"


async def classify_document(raw_text: str) -> str:
    """규칙 기반 1차 → OTHER일 때 GPT 2차 분류.

    Returns:
        "PRESCRIPTION" | "DRUG_BAG" | "OTHER"
    """
    if len(raw_text.strip()) < 30:
        return "OTHER"

    result = _rule_classify(raw_text)
    if result is not None:
        logger.info("규칙 기반 문서 분류 결과: %s", result)
        return result

    result = await _ai_classify(raw_text)
    logger.info("AI 문서 분류 결과: %s", result)
    return result
