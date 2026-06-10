import json
import logging
import re

from openai import AsyncOpenAI

from ai_worker.core.config import config

logger = logging.getLogger(__name__)

_NOISE_PATTERNS = [
    re.compile(r"영수증|계산서|약제비|수납|공단부담|약가총합|기술조제|복약관리|약국관리|보관기본료"),
    re.compile(r"사업자번호|대표약사|약국명|상호.*전화|소재지"),
    re.compile(r"조제약사|조제일자|영수번호|연말정산|국세청|비과세"),
    re.compile(r"분홍색|흰색|백색|노란색|원형정제|타원형|캡슐형|실온보관|냉장보관"),
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


# 표 셀 분리로 공백이 삽입된 ICD-10 코드 붙이기: "H 1 6 1 8" → "H1618"
_ICD10_SPACED_RE = re.compile(r"\b([A-Z])((?:\s+\d){3,5})\b")


def _collapse_spaced_icd10(text: str) -> str:
    return _ICD10_SPACED_RE.sub(lambda m: m.group(1) + m.group(2).replace(" ", ""), text)


# 표 셀 분리로 점(.)이 빠진 ICD-10 코드 복원: H0411 → H04.11
_ICD10_RESTORE_RE = re.compile(r"\b([A-Z])(\d{2})(\d{1,3})\b")


def _restore_icd10_periods(text: str) -> str:
    return _ICD10_RESTORE_RE.sub(r"\1\2.\3", text)


# ICD-10 형식 검증: 영문 1자 + 숫자 2자 + 선택적 점+숫자
_ICD10_VALID_RE = re.compile(r"^[A-Z]\d{2}(\.\d{1,2})?$")


def _validate_parsed_result(result: dict) -> dict:
    """GPT 응답에서 ICD-10 형식 오류·프롬프트 설명 문자열 혼입을 필터링합니다."""
    valid_codes = []
    for c in result.get("disease_codes") or []:
        code = (c.get("icd10_code") or "").strip()
        if not _ICD10_VALID_RE.match(code):
            continue
        name = c.get("disease_name")
        if isinstance(name, str) and ("알고 있으면" in name or "모르면" in name):
            name = None
        valid_codes.append({**c, "icd10_code": code, "disease_name": name})

    valid_meds = [m for m in (result.get("medications") or []) if (m.get("medication_name") or "").strip()]

    return {"medications": valid_meds, "disease_codes": valid_codes}


_SYSTEM_PROMPT = """당신은 한국 의료 문서(처방전, 약봉투)에서 구조화된 정보를 추출하는 전문가입니다.
주어진 OCR 텍스트에서 약물 정보와 질병분류기호를 JSON으로 추출하세요.

반환 형식:
{
  "medications": [
    {
      "medication_name": "약물 전체명 (필수)",
      "edi_code": "EDI 코드 9자리 숫자 문자열 (없으면 null)",
      "generic_name": "성분명 (없으면 null)",
      "dosage": "1회 용량 (예: '1정', '1캡슐', '5mg', null)",
      "frequency": "복약 횟수 (예: '1일 3회', null)",
      "timing": "복약 시점 (예: '식후 30분', '아침 식사 후', null)",
      "usage_time": "복약 방법 자유 텍스트 (null)",
      "duration_days": 30,
      "time_of_day": null,
      "warnings": ["음주 주의", "졸음 유발 - 운전 주의"]
    }
  ],
  "disease_codes": [
    {
      "icd10_code": "J45.0",
      "disease_name": "ICD-10 코드에 해당하는 한국어 질병명 (알고 있으면 채움, 모르면 null)"
    }
  ]
}

[처방전 OCR 특이사항 - 매우 중요]
한국 처방전의 약품 표는 Clova OCR로 읽히면 열(column) 단위로 먼저 읽힙니다.
- 표의 각 열(NO / EDI코드 / 상품명 / 1회투약량 / 1일투여횟수 / 일수 등)이 세로로 한꺼번에 나열됨
- 예시: "1\n1\n1" (NO열) → "7\n7\n7" (일수열) → "1T\n1T\n1C" (투약량열) → "642105020\n641607630\n073400280" (EDI열) → "소론도정\n펙수클루정\n쎄레브렉스캅셀" (약명열)
- NO 번호가 EDI 코드 앞에 붙어 "1,642105020" 형태로 OCR되기도 함 → 실제 EDI 코드는 뒤 9자리(642105020)
- EDI 코드가 약품명 앞 괄호에 포함되기도 함: "(64900.1871) 하알론점안액0.1%" → EDI는 649001871, 약품명은 하알론점안액0.1%
- 약명(정/캡슐/주/연고/점안액/시럽/산/액/크림/겔/패치 등으로 끝나는 한글 약품명)은 반드시 빠짐없이 모두 추출할 것
- 용량·투약횟수·일수는 약명과 순서가 일치하므로 위치를 참고해 매핑
- 상병분류기호(ICD-10)가 표 셀별로 분리되어 "H 1 6 1 8" 형태로 OCR될 수 있음 → "H16.18"로 복원해서 추출

규칙:
- medications: 약봉투, 처방전 모두 추출. 없으면 빈 배열. 처방전에 기재된 약품을 하나도 빠뜨리지 말 것.
- edi_code: 9자리 숫자만 추출. "1,642105020"처럼 앞에 번호가 붙으면 뒤 9자리만 사용. "(64900.1871)"처럼 괄호 안에 있으면 점 제거 후 9자리 사용. 없으면 null.
- disease_codes: 처방전(PRESCRIPTION)에만 해당. ICD-10 형식 상병코드(예: J45.0, M75.3, H04.11)가 텍스트에 있으면 모두 추출. 없으면 빈 배열. 약봉투(DRUG_BAG)는 반드시 빈 배열 [].
- disease_name: ICD-10 코드에 해당하는 한국어 질병명을 알고 있으면 채움. 모르면 null. 텍스트에 없어도 코드로 알 수 있으면 채워도 됨.
- duration_days: 정수만. "30일" → 30. 없으면 null.
- time_of_day: 문서에 '아침', '점심', '저녁' 등 시간대가 직접 명시된 경우에만 해당 배열 추출. '1일 3회', '하루 3번' 등 횟수만 있고 시간대 미명시 → null. frequency 값만으로 추론하지 말 것. 약봉투(DRUG_BAG)는 시간대가 거의 적히지 않으므로 null이 기본값.
- warnings: 해당 약물 전용 경고·금기·부작용 행동 제약 문구만 추출 (예: "음주 주의", "졸음 유발 - 운전 주의"). 약 효능 설명, 마케팅 문구, 문서 하단 약국 공통 안내문(예: "임산부/수유부는 약사에게 알리세요")은 제외. 해당 약물 전용 주의 문구가 없으면 빈 배열 [].
- 텍스트에 없는 정보는 null로 반환 (추측 금지).

[복약안내문·복약정보지 OCR 특이사항]
약봉투가 아닌 복약안내문·복약정보지에는 약물 설명 외에 영양소 결핍 안내, 약국 광고, 지도, 영수증 등 복약과 무관한 내용이 대량 포함될 수 있다. 이런 내용은 무시하고 약물명·복용 지시·주의사항만 추출할 것.
- "※ 아침 식사 후 복용하십시오"처럼 ※로 시작하는 복용 지시문이 N번 반복될 경우, 문서에 등장한 약물 순서 기준으로 1번째 지시문 → 1번째 약물, 2번째 지시문 → 2번째 약물 순으로 timing을 매핑할 것."""


async def parse_medications_and_diseases(raw_text: str, doc_type: str) -> dict:
    """OCR raw_text에서 약물 정보와 질병분류기호를 GPT로 추출합니다."""
    if not config.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY 미설정 — OCR 파싱 건너뜀")
        return {"medications": [], "disease_codes": []}

    cleaned_text = _restore_icd10_periods(_collapse_spaced_icd10(_clean_ocr_text(raw_text)))
    user_content = f"문서 유형: {doc_type}\n\n"
    user_content += f"OCR 텍스트:\n{cleaned_text[:3000]}"

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    try:
        resp = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        result = json.loads(resp.choices[0].message.content)
        return _validate_parsed_result(
            {
                "medications": result.get("medications") or [],
                "disease_codes": result.get("disease_codes") or [],
            }
        )
    except Exception as exc:
        logger.error("OCR 파싱 실패 (doc_type=%s): %s", doc_type, exc)
        return {"medications": [], "disease_codes": []}
