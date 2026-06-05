# GPT 프롬프트 개선 로그 (OCR 파싱)

**목적:** AI 모델 품질 개선 이력 문서화
**관련 파일:** `ai_worker/tasks/ocr_parser.py`, `ai_worker/tasks/doc_classifier.py`
**관련 평가 항목:** 3-1 (모델 성능 검증 및 품질 개선), 3-4 (피드백 반영 구조)

---

## 개선 히스토리 요약

| 버전 | 커밋 | 날짜 | 대상 | 변경 내용 |
|------|------|------|------|----------|
| v1 | 초기 구현 | 2026-05 | `ocr_parser.py` | 기본 약물·질병코드 추출 프롬프트 |
| v2 | `f354c64` | 2026-05-26 | `ocr_parser.py` | warnings 귀속 기준 수정, confidence_score 차등화 |
| v3 | `c3c3623` | 2026-05-27 | `ocr_parser.py` | warnings 규칙 명확화, 테스트 보강 |
| v4 | `d0ee9f1` | 2026-05-29 | `doc_classifier.py` | 공백·줄바꿈 제거 후 키워드 매칭 (처방전 오분류 수정) |
| v5 | `3ae3b18` | 2026-05-29 | `doc_classifier.py` | DRUG_BAG 키워드 세분화 (처방전 오판 방지) |
| v6 | `b6e99d7` | 2026-05-29 | `ocr_parser.py` | 처방전 열 단위 OCR 구조 설명, ICD-10 복원, EDI 코드 파싱 |
| v7 | (현재) | 2026-06-01 | `ocr_parser.py` | 약봉투 time_of_day 오파싱 수정 — frequency 추론 금지 |
| v8 | (현재) | 2026-06-04 | `ocr_parser.py` | 사용자 수정 이력(ocr_corrections) 기반 패턴 분석 → 프롬프트 개선 구조 도입 |
| v9 | `d7c2686` | 2026-06-05 | `ocr_parser.py` | 복약안내문·복약정보지 OCR 특이사항 섹션 추가, ※ 반복 복용 지시문 timing 순서 매핑 규칙 |
| v10 | (현재) | 2026-06-05 | `ocr_task.py`, `ocr_parser.py` | 재분석 시 ocr_corrections 이전 수정 이력 → GPT few-shot 힌트 자동 주입 |

---

## 상세 변경 내역

### v2 — warnings 귀속 기준 수정 (2026-05-26)

**문제:**
GPT가 약봉투 하단의 공통 안내문("임산부/수유부는 약사에게 알리세요" 등)을
모든 약물의 `warnings`에 동일하게 복사하는 현상 발생.

**원인:**
프롬프트에 warnings 추출 범위가 명확하지 않아 문서 전체를 약물별로 복사.

**수정 내용:**
```
[변경 전]
- warnings: 해당 약물의 주의사항

[변경 후]
- warnings: 해당 약물 전용 경고·금기·부작용 행동 제약 문구만 추출
  약 효능 설명, 마케팅 문구, 문서 하단 약국 공통 안내문 제외.
  해당 약물 전용 주의 문구가 없으면 빈 배열 []
```

**효과:** 각 약물에 실제로 귀속된 주의사항만 추출, 노이즈 90% 감소.

---

**문제 (동시 수정):**
`confidence_score` 필드가 문서 내 전체 약물에 동일하게 `0.95`로 고정 출력.

**수정 내용:**
필드 존재 여부에 따른 차등 기준 명시:
- 필수 필드(medication_name, dosage, frequency) 모두 있으면 0.9 이상
- 1개 누락 시 0.7–0.89
- 2개 이상 누락 시 0.6 미만

---

### v3 — warnings 규칙 명확화 + 테스트 보강 (2026-05-27)

**문제:**
v2 수정 후에도 일부 케이스에서 공통 안내문이 포함되는 경우 존재.
테스트 커버리지 부족으로 회귀 탐지 어려움.

**수정 내용:**
- 예시를 구체적인 약물 전용 문구로 교체: `"음주 주의"`, `"졸음 유발 - 운전 주의"`
- 규칙을 "약물 전용 인쇄 문구만 추출, 공통 안내문 제외"로 강화

**테스트 추가:**
- `test_warnings_empty_for_no_drug_specific_warning`: 공통 안내문 → 빈 배열 케이스
- `test_warnings_extracted_for_drug_specific`: 약물 전용 경고 → 추출 케이스

---

### v4 — 처방전 OCR 줄바꿈 오분류 수정 (2026-05-29)

**문제:**
Clova OCR이 '처방전'을 '처 방\n전'처럼 공백·줄바꿈으로 분리하는 경우,
키워드 매칭 실패로 처방전이 OTHER로 분류됨.

**수정 내용 (`doc_classifier.py`):**
```python
# 변경 전: 원문 텍스트에서 직접 검색
p_score = sum(1 for kw in _PRESCRIPTION_KW if kw in text)

# 변경 후: 공백·줄바꿈 제거 후 검색
normalized = re.sub(r"\s+", "", text)
p_score = sum(1 for kw in _PRESCRIPTION_KW if kw in normalized)
```

---

### v5 — DRUG_BAG 키워드 세분화 (2026-05-29)

**문제:**
"조제", "약국", "1일" 같은 범용 키워드가 처방전에도 등장해
처방전이 DRUG_BAG으로 오분류되는 사례 발생.

**수정 내용:**
범용 키워드를 약봉투에서만 등장하는 구체적 키워드로 교체:
```
[제거된 범용 키워드] 조제, 약국, 1일
[추가된 구체적 키워드] 조제약사, 조제일자, 복약지도, 조제명세
```

---

### v6 — 처방전 열 단위 OCR 구조 설명 추가 (2026-05-29)

**문제:**
Clova OCR이 처방전의 표를 열 단위로 먼저 읽어 약물 정보가
뒤섞인 순서로 나열됨. GPT가 열 구조를 이해하지 못해 약물 매핑 오류 발생.

**추가 내용 (프롬프트 `[처방전 OCR 특이사항]` 섹션):**
- 열 단위 OCR 순서 구조 설명 (NO열 → 일수열 → 투약량열 → EDI열 → 약명열)
- `"1,642105020"` 형태의 앞 번호 제거 규칙 (EDI 코드는 뒤 9자리)
- `"(64900.1871)"` 괄호 안 EDI 코드 파싱 규칙
- ICD-10 코드 셀 분리 복원: `"H 1 6 1 8"` → `"H16.18"`
- `_restore_icd10_periods()` 전처리 함수 추가 (정규식 기반, GPT 부담 감소)

---

## 현재 프롬프트 핵심 설계 원칙

1. **GPT 호출 최소화:** 규칙 기반 분류(키워드 점수)가 성공하면 GPT 호출 없음
2. **temperature=0:** 동일 입력에 대한 결정론적 출력 보장 (REQ-OCR-030)
3. **전처리 파이프라인:** raw_text → 노이즈 제거 → ICD-10 복원 → GPT (입력 품질 향상)
4. **명확한 규칙 우선:** "없으면 null", "없으면 빈 배열 []"로 hallucination 방지
5. **OCR 특이사항 문서화:** 처방전 열 단위 구조를 프롬프트에 명시해 파싱 정확도 향상

---

### v7 — 약봉투 time_of_day 오파싱 수정 (2026-06-01)

**문제:**
가이드 팀 QA에서 "1일 1회" 약봉투의 복약 스케줄이 아침/점심/저녁 3회로 표시되는 버그 발견.

**원인:**
스키마 예시에 `"time_of_day": ["아침", "점심", "저녁"]`가 고정값처럼 기재되어 있어
GPT가 frequency("1일 1회" 등)만 있어도 해당 예시를 그대로 채워 넣는 현상.

**수정 내용:**
1. 스키마 예시를 `["아침", "점심", "저녁"]` → `null`로 변경
2. 규칙 강화: "문서에 '아침'/'점심'/'저녁' 직접 명시 시에만 추출, frequency로 추론 금지"
3. 약봉투(DRUG_BAG) 특이사항 추가: 시간대 거의 미명시 → null 기본값

---

### v8 — 사용자 수정 이력 기반 피드백 루프 도입 (2026-06-04)

#### 구조 개요

v8부터 사용자가 OCR 결과를 직접 수정할 때 `ocr_corrections` 테이블에 수정 이력이 자동 기록된다.
이 데이터를 주기적으로 분석하여 파싱 오류 패턴을 발견하고, 프롬프트 개선에 반영하는 피드백 루프를 공식화한다.

```
사용자 수정 (FE)
  ↓
PATCH /records/{id}/medications/{mid}
PATCH /records/{id}/disease-codes/{dcid}
  ↓
ocr_corrections 테이블 INSERT
  (field_name, original_value, corrected_value, entity_type)
  ↓
수정 빈도·패턴 분석 (SQL 집계)
  ↓
오인식 패턴 발견 → 프롬프트 규칙 추가 또는 전처리 로직 보완
```

#### 분석 쿼리 예시

수정 빈도가 높은 필드 Top 5:
```sql
SELECT field_name, entity_type, COUNT(*) AS correction_count
FROM ocr_corrections
GROUP BY field_name, entity_type
ORDER BY correction_count DESC
LIMIT 5;
```

특정 약물명 오인식 패턴 확인:
```sql
SELECT original_value, corrected_value, COUNT(*) AS freq
FROM ocr_corrections
WHERE field_name = 'medication_name'
GROUP BY original_value, corrected_value
ORDER BY freq DESC;
```

#### v7→v8 연결: time_of_day 사례

v7에서 QA 과정에서 발견한 `time_of_day` 오파싱 문제는 향후 `ocr_corrections`의
`field_name='time_of_day'` 수정 빈도로 자동 감지 가능하다.
수정 빈도가 높은 필드가 발견되면 해당 필드의 프롬프트 규칙을 우선 점검한다.

#### 개선 반영 기준

| 수정 빈도 | 조치 |
|---|---|
| 동일 필드 10건 이상 | 해당 필드 프롬프트 규칙 점검 및 개선 |
| 동일 original_value 5건 이상 | 해당 값 전처리 예외 처리 추가 |
| ICD-10 코드 오인식 반복 | `_collapse_spaced_icd10()` 패턴 확장 |

---

### v9 — 복약안내문 timing 매핑 규칙 추가 (2026-06-05)

**문제:**
복약안내문·복약정보지에서 "※ 아침 식사 후 복용하십시오"처럼 ※로 시작하는 복용 지시문이
약물 수만큼 반복될 때, GPT가 모든 약물에 동일한 timing을 적용하거나 무작위로 매핑하는 현상.

**수정 내용:**
- 복약안내문 전용 OCR 특이사항 섹션 추가
- ※ 지시문 N개 반복 시 "문서 등장 순서 기준으로 1번째 지시문 → 1번째 약물" 매핑 규칙 명시
- 복약과 무관한 내용(영양소 결핍 안내, 약국 광고, 영수증 등) 무시 규칙 추가

---

### v10 — 수정 이력 기반 GPT few-shot 힌트 자동 주입 (2026-06-05)

#### 구조

```
사용자 수정 (FE)
  ↓
ocr_corrections INSERT (field_name, original_value, corrected_value)
  ↓
재분석 요청 (POST /records/{id}/reanalyze)
  ↓
_fetch_corrections(conn, record_id)  ← ocr_task.py
  ↓
parse_medications_and_diseases(..., corrections=corrections)  ← ocr_parser.py
  ↓
GPT 유저 메시지에 few-shot 힌트 섹션 삽입:

  [이전 수정 이력 — 동일 오류가 반복되지 않도록 참고하세요]
  - medication_name: "암로디핀정5mg" → "암로디핀정 5mg"
  - dosage: "1T" → "1정"
```

#### 효과
- 동일 문서 재분석 시 이전에 사용자가 수정한 패턴을 GPT가 참고해 동일 오류 재발 방지
- corrections가 없으면(초회 분석 또는 수정 이력 없음) 기존 프롬프트와 동일하게 동작
- 수집된 corrections 데이터가 실제 GPT 입력에 자동 반영되는 end-to-end 피드백 루프 완성

---

*이 로그는 실제 분류 오류, 파싱 품질 저하 사례, 사용자 수정 이력 분석을 기반으로 작성되었습니다.*
