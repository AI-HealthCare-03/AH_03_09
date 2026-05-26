import json
import logging

from openai import AsyncOpenAI

from ai_worker.core.config import config

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """당신은 한국 의료 문서(처방전, 약봉투)에서 구조화된 정보를 추출하는 전문가입니다.
주어진 OCR 텍스트에서 약물 정보와 질병분류기호를 JSON으로 추출하세요.

반환 형식:
{
  "medications": [
    {
      "medication_name": "약물 전체명 (필수)",
      "edi_code": "EDI 코드 9자리 (없으면 null)",
      "generic_name": "성분명 (없으면 null)",
      "dosage": "1회 용량 (예: '1정', '5mg', null)",
      "frequency": "복약 횟수 (예: '1일 3회', null)",
      "timing": "복약 시점 (예: '식후 30분', null)",
      "usage_time": "복약 방법 자유 텍스트 (null)",
      "duration_days": 30,
      "time_of_day": ["아침", "점심", "저녁"],
      "warnings": ["주의사항"],
      "confidence_score": 0.85
    }
  ],
  "disease_codes": [
    {
      "icd10_code": "J45.0",
      "disease_name": "기관지천식",
      "confidence_score": 0.95
    }
  ]
}

규칙:
- medications: 약봉투, 처방전 모두 추출. 없으면 빈 배열.
- edi_code: 처방전의 EDI 코드(9자리 숫자 문자열). 없으면 null.
- disease_codes: 처방전에 있는 모든 상병코드를 추출. 여러 개면 모두 포함. 없거나 약봉투면 빈 배열.
- duration_days: 정수만. "30일" → 30. 없으면 null.
- time_of_day: 추론 가능한 경우만 배열 (예: ["아침", "저녁"]), 불명확하면 null.
- confidence_score: 약물별로 개별 산정. 약명·용량·복약법·기간이 모두 명확하면 0.90 이상, 일부 필드(dosage, timing, duration_days 등)가 누락되거나 불명확하면 0.70~0.89, 약명만 있고 나머지 대부분 누락이면 0.70 미만. 같은 문서 내 모든 약에 동일한 점수를 부여하지 말 것.
- warnings: 해당 약물에 직접 연결된 주의사항만 추출. 문서 하단의 일반 안내문(예: "임산부/수유부는 약사에게 알리세요")처럼 특정 약물에 귀속되지 않는 내용은 제외. 약별 개별 주의사항이 없으면 빈 배열 [].
- 텍스트에 없는 정보는 null로 반환 (추측 금지)."""


async def parse_medications_and_diseases(raw_text: str, doc_type: str) -> dict:
    """OCR raw_text에서 약물 정보와 질병분류기호를 GPT로 추출합니다."""
    if not config.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY 미설정 — OCR 파싱 건너뜀")
        return {"medications": [], "disease_codes": []}

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"문서 유형: {doc_type}\n\nOCR 텍스트:\n{raw_text[:3000]}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        result = json.loads(resp.choices[0].message.content)
        return {
            "medications": result.get("medications") or [],
            "disease_codes": result.get("disease_codes") or [],
        }
    except Exception as exc:
        logger.error("OCR 파싱 실패 (doc_type=%s): %s", doc_type, exc)
        return {"medications": [], "disease_codes": []}
