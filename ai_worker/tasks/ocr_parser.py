import json
import logging
import re

from openai import AsyncOpenAI

from ai_worker.core.config import config

logger = logging.getLogger(__name__)

_NOISE_PATTERNS = [
    re.compile(r"영수증|계산서|약제비|수납|본인부담|공단부담|약가총합|기술조제|복약관리|약국관리|보관기본료"),
    re.compile(r"사업자번호|대표약사|약국명|상호.*전화|소재지"),
    re.compile(r"조제약사|조제일자|영수번호|연말정산|국세청|비과세"),
    re.compile(r"분홍색|흰색|백색|노란색|원형정제|타원형|캡슐형|실온보관|냉장보관"),
    re.compile(r"^\s*[\d,]+\s*$"),  # 금액 숫자만 있는 줄
    re.compile(r"RECEIPT|PATIENT-\d+|RX-\d+|MEDICAL-MOCK"),  # 테스트 태그
    re.compile(r"^\s*[.。·■●◆▶▷※\-\*]+\s*$"),  # 특수문자만 있는 줄
    # 모든 약봉투에 인쇄되는 법정 공통 안내문 (약물별 경고 아님)
    re.compile(r"임산부.{0,15}수유부"),
    re.compile(r"어린이.{0,10}손.{0,10}닿지"),
    re.compile(r"의약품\s*부작용\s*신고"),
    re.compile(r"약을?\s*먹기\s*전|이\s*약을?\s*사용하기\s*전"),
]


def _clean_ocr_text(raw_text: str) -> str:
    """OCR 원문에서 영수증·약국 행정 정보 등 파싱에 불필요한 노이즈 라인을 제거합니다."""
    lines = raw_text.splitlines()
    cleaned = [line for line in lines if not any(p.search(line) for p in _NOISE_PATTERNS)]
    return "\n".join(cleaned)


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
      "warnings": ["음주 주의", "졸음 유발 - 운전 주의"]
    }
  ],
  "disease_codes": [
    {
      "icd10_code": "J45.0",
      "disease_name": "기관지천식"
    }
  ]
}

규칙:
- medications: 약봉투, 처방전 모두 추출. 없으면 빈 배열.
- edi_code: 처방전의 EDI 코드(9자리 숫자 문자열). 없으면 null.
- disease_codes: 처방전에 있는 모든 상병코드를 추출. 여러 개면 모두 포함. 없거나 약봉투면 빈 배열.
- duration_days: 정수만. "30일" → 30. 없으면 null.
- time_of_day: 추론 가능한 경우만 배열 (예: ["아침", "저녁"]), 불명확하면 null.
- warnings: 약봉투·처방전에 인쇄된 해당 약물 전용 주의 문구만 추출 (예: "음주 주의", "졸음 유발 - 운전 주의"). 문서 하단의 약국 공통 안내문(예: "임산부/수유부는 약사에게 알리세요")은 제외. 해당 약물의 주의 문구가 없으면 빈 배열 [].
- 텍스트에 없는 정보는 null로 반환 (추측 금지)."""


async def parse_medications_and_diseases(raw_text: str, doc_type: str) -> dict:
    """OCR raw_text에서 약물 정보와 질병분류기호를 GPT로 추출합니다."""
    if not config.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY 미설정 — OCR 파싱 건너뜀")
        return {"medications": [], "disease_codes": []}

    cleaned_text = _clean_ocr_text(raw_text)
    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"문서 유형: {doc_type}\n\nOCR 텍스트:\n{cleaned_text[:3000]}",
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
