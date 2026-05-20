# OCR → schedule_table Mapping 정책 (MVP 최종안)

---

# 1. 목적

OCR API 결과를 기반으로:

- 복약 스케줄(schedule_table)
- LLM medication guide 생성 입력 데이터

로 변환하기 위한 MVP 기준 정책 정의.

---

# 2. OCR 응답 구조 예시

```json
{
  "name": "암로디정 5mg",
  "generic_name": "암로디핀",
  "dosage": "1정",
  "frequency": "1일 1회",
  "timing": "식후 30분",
  "time_of_day": ["아침"],
  "warnings": ["졸음 주의"],
  "route": "경구",
  "confidence_score": 91.2,
  "confidence_level": "높음"
}
```

`generic_name`은 optional 필드로 처리하며, OCR 또는 내부 매핑 결과가 없는 경우 null 또는 빈값 허용 가능.

예시:

```json
{
  "name": "노바스크정5mg",
  "generic_name": null
}
```

---

# 3. schedule_table Mapping 정의

| OCR 필드 | schedule_table 필드 | 목적 | 처리 원칙 |
|---------|-------------------|------|---------|
| name | medication_name | 약명 표시 | OCR 원문 유지 |
| generic_name | generic_name | 참고용(optional) | 선택 사용 |
| dosage | dosage | 복용량 표시 | OCR 원문 유지 |
| frequency | frequency | 복용 주기 표시 | OCR 원문 유지 |
| timing | timing | 복용 시점 표시 | OCR 원문 유지 |
| usage_time | usage_time | 화면 표시용 자유 텍스트 | OCR frequency/timing 기반 생성 |
| time_of_day | time_of_day | UI schedule slot 표시 | 제한적 UI 정규화 허용 |
| warnings | cautions | 주의사항 표시 | OCR 값 우선 |
| route | administration_route | 복용 경로 | OCR 원문 유지 |
| confidence_score | ocr_confidence | OCR 신뢰도 표시 | 프론트 경고 정책 활용 |
| confidence_level | confidence_level | 사용자 확인 정책 | 낮음 시 확인 필요 표시 |

---

# 4. frequency / timing / usage_time 처리 정책

## 기본 원칙

- `frequency`, `timing`은 OCR 원문 의미를 유지한다.
- `usage_time`은 자유 텍스트 기반으로 유지한다.
- `usage_time`은 사용자 화면 표시 및 guide 생성 입력 양쪽에 사용된다.
- OCR에 없는 정확한 복용 시간(HH:MM)은 생성하지 않는다.

---

# 5. time_of_day 처리 정책

## 목적

아침 / 점심 / 저녁 기반 복약 스케줄 UI 구성을 위한 제한적 schedule slot 정보.

`time_of_day`는 정확한 복용 시간을 의미하지 않는다.

## 기본 원칙

- `time_of_day`는 UI 표시 목적의 일반화된 schedule slot으로만 사용한다.
- 정확한 복용 시간(HH:MM) 생성은 금지한다.
- 제한적 UI 정규화만 허용한다.
- OCR 원문 의미를 변경하지 않는다.
- 아래 허용 예시 테이블에 없는 패턴은 time_of_day 미생성, usage_time만 표시한다.

## 허용 예시

| OCR frequency | OCR timing | time_of_day |
|--------------|------------|-------------|
| 1일 3회 | 식후 30분 | ["아침","점심","저녁"] |
| 1일 2회 | 식후 | ["아침","저녁"] |
| 1일 1회 | 아침 식후 | ["아침"] |

> 위 정규화는 프론트엔드 스케줄 UI 렌더링 목적으로만 사용되며, 정확한 의학적 복용 시각을 의미하지 않는다.

## 비허용 예시

| OCR 입력 | 금지 처리 |
|---------|---------|
| 식후 30분 | 08:30 자동 생성 |
| 주1회 | 월요일 자동 지정 |
| 필요시 | 임의 복용 간격 생성 |
| 격일 | 특정 날짜 자동 생성 |

---

# 6. usage_time 처리 정책

## 목적

`time_of_day` enum만으로 표현하기 어려운 복약 지시를 사용자 화면에 표시하기 위한 자유 텍스트 필드.

## 저장 예시

| OCR frequency | OCR timing | usage_time |
|--------------|------------|------------|
| 1일 3회 | 식후 30분 | 1일 3회, 식후 30분 |
| 주1회 | 지정일 복용 | 주1회, 지정일 복용 |
| 격일 | 식후 | 격일, 식후 |
| 필요시 | 통증 시 | 필요시, 통증 시 |
| 1일 1회 | 취침 전 | 취침 전 |

> timing이 단독으로 복약 지시를 완전히 표현하는 경우(취침 전, 필요시 등) frequency 생략 가능.

## null 처리 정책

- `frequency` 또는 `timing`이 비어 있는 경우 존재하는 OCR 원문만 사용한다.
- 존재하지 않는 정보는 생성하지 않는다.
- `frequency`, `timing` 모두 null이면 `usage_time` = null (미생성).

| frequency | timing | usage_time |
|-----------|--------|------------|
| null | 식후 30분 | 식후 30분 |
| 1일 1회 | null | 1일 1회 |
| null | null | null |

---

# 7. OCR 신뢰도 처리 정책

## confidence_level 활용

| OCR 신뢰도 | 프론트 정책 |
|----------|-----------|
| 높음 | 일반 표시 |
| 중간 | 확인 권장 |
| 낮음 | 사용자 확인 필요 표시 |

## 낮은 신뢰도 표시 예시

> OCR 인식 정확도가 낮아 확인이 필요합니다.

---

# 8. 질병코드 처리 정책

## 목적

OCR 질병코드는 생활/식사/운동 가이드 생성 여부 판단에만 사용한다.

## 기본 원칙

- 질병코드가 여러 개인 경우에도 시스템이 대표질환을 자동으로 판단하지 않는다.
- Whitelist 대상 질환만 생활/식사/운동 가이드 생성에 사용한다.
- 생활가이드는 일반 건강관리 참고 수준으로 제한한다.

## 질병 정보 출처 우선순위

1. 처방전 질병코드
2. 약봉투 질병기호
3. 사용자 직접 입력 질환

상위 우선순위 출처가 존재하면 해당 출처를 우선 사용하며, 해당 출처 내에서 whitelist 대상 질환만 필터링한다.

## 현재 whitelist 후보 질환

- 고혈압
- 당뇨
- 고지혈증
- 위염
- 역류성식도염
- 변비
- 골관절염
- 알레르기비염

## 다중 질환 처리

whitelist 대상 질환이 여러 개인 경우:

- 질환별 일반 건강관리 참고정보 수준의 가이드를 생성 가능
- 표시 개수 및 UI 구성은 프론트 정책에 따라 제한 가능

---

# 9. Guide 생성 입력 정책

| 필드 | 활용 목적 |
|-----|---------|
| medication_name | 약 guide 검색 |
| generic_name | 참고용(optional) |
| dosage | 표시용 |
| frequency | 복용 주기 표시 |
| timing | 복용 시점 표시 |
| usage_time | 자유 텍스트 복약 표시 |
| warnings | 주의사항 |
| disease_codes | 생활가이드 여부 판단 |

---

# 10. NOT_FOUND 정책

## 식약처 CSV 미매칭 시

식약처 CSV 기반 약물 정보가 없는 경우에도 일반 LLM 기반 참고 설명은 제공 가능하다.

단, 공공데이터 기반 정보가 아님을 명시적으로 표시한다.

## 표시 예시

> 해당 의약품은 식약처 CSV 데이터에서 찾을 수 없습니다.
>
> 아래 내용은 일반 LLM 지식 기반 참고 설명이며,
> 복용 전 약사 또는 의료진에게 확인이 필요합니다.

---

# 11. 프론트 표시 정책

## usage_time 우선 표시

`usage_time`은 사용자 화면에 직접 표시되는 기본 복약 설명 필드로 사용한다.

## 스케줄 카드 정책

| 조건 | 프론트 처리 |
|-----|-----------|
| time_of_day 존재 | 아침/점심/저녁 slot 카드 표시 |
| time_of_day 없음 | usage_time 자유 텍스트 표시 |

---

# 12. 안전 정책 (Safety Policy)

시스템은 다음을 수행하지 않는다:

- OCR에 없는 정확한 복용시간(HH:MM) 생성
- 복용량 보정
- 복용횟수 임의 추론
- 질병 확정
- 약물 변경 권고
- 치료 계획 변경
- 모호한 OCR 지시 임의 정규화
- 대표 질환 자동 선정
