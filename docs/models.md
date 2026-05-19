# 데이터 모델 정의서

> ORM: Tortoise ORM / DB: MySQL / 마이그레이션: Aerich

---

## 목차

1. [엔티티 관계도](#엔티티-관계도)
2. [User](#1-user)
3. [ChatSession / ChatMessage](#2-chatsession--chatmessage)
4. [HealthProfile / HealthProfileHistory](#3-healthprofile--healthprofilehistory)
5. [MedicalDocument / OCRResult](#4-medicaldocument--ocrresult)
6. [Medication](#5-medication)
7. [HealthGuidance](#6-healthguidance)
8. [Enum 목록](#enum-목록)

---

## 엔티티 관계도

```
User (1)─────────────────────────────────────────────────────(N) ChatSession
 │                                                                    │
 │                                                                (N) ChatMessage
 │
 ├──(1:1) HealthProfile ──(N) HealthProfileHistory
 │             │
 │             └──(N) HealthGuidance
 │
 ├──(N) MedicalDocument ──(1) OCRResult
 │             │
 │             └──(N) Medication (nullable FK)
 │
 ├──(N) Medication
 └──(N) HealthGuidance
```

---

## 1. User

**파일:** `app/models/users.py` | **테이블:** `users`

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | BIGINT | PK, AUTO_INCREMENT | - |
| `email` | VARCHAR(40) | NOT NULL | 로그인 이메일 |
| `hashed_password` | VARCHAR(128) | NOT NULL | bcrypt 해시 |
| `name` | VARCHAR(20) | NOT NULL | 사용자 이름 |
| `gender` | ENUM | NOT NULL | `MALE` / `FEMALE` |
| `birthday` | DATE | NOT NULL | 생년월일 |
| `phone_number` | VARCHAR(11) | NOT NULL | 휴대폰 번호 |
| `is_active` | BOOLEAN | DEFAULT TRUE | 계정 활성 여부 (30일 비활성 시 자동 비활성화) |
| `is_admin` | BOOLEAN | DEFAULT FALSE | 관리자 여부 |
| `last_login` | DATETIME(6) | NULL | 마지막 로그인 시각 |
| `created_at` | DATETIME(6) | AUTO | 생성 시각 |
| `updated_at` | DATETIME(6) | AUTO | 수정 시각 |

---

## 2. ChatSession / ChatMessage

**파일:** `app/models/chats.py`

### ChatSession — 테이블: `chat_sessions`

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | BIGINT | PK | - |
| `user_id` | BIGINT | FK → users(id) CASCADE | 소유 사용자 |
| `title` | VARCHAR(100) | DEFAULT '새 대화' | 대화 제목 |
| `created_at` | DATETIME(6) | AUTO | - |
| `updated_at` | DATETIME(6) | AUTO | - |

### ChatMessage — 테이블: `chat_messages`

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | BIGINT | PK | - |
| `session_id` | BIGINT | FK → chat_sessions(id) CASCADE | 소속 세션 |
| `role` | ENUM | NOT NULL | `USER` / `ASSISTANT` |
| `content` | LONGTEXT | NOT NULL | 메시지 내용 |
| `created_at` | DATETIME(6) | AUTO | 기본 정렬 기준 |

---

## 3. HealthProfile / HealthProfileHistory

**파일:** `app/models/health_profiles.py`

### HealthProfile — 테이블: `health_profiles`

사용자당 하나의 건강 프로필. `user_id`에 UNIQUE 제약이 걸려 1:1 관계를 보장한다.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | BIGINT | PK | - |
| `user_id` | BIGINT | FK → users(id) CASCADE, UNIQUE | 소유 사용자 |
| `primary_conditions` | JSON | DEFAULT `[]` | 진단명 목록 |
| `allergies` | JSON | DEFAULT `[]` | 알레르기 목록 |
| `current_medications` | JSON | DEFAULT `[]` | 현재 복용 중인 약물 목록 |
| `lifestyle_exercise` | ENUM | DEFAULT `NONE` | 운동 습관 (`REGULAR` / `IRREGULAR` / `NONE`) |
| `lifestyle_smoking` | BOOLEAN | DEFAULT FALSE | 흡연 여부 |
| `lifestyle_alcohol` | ENUM | DEFAULT `NONE` | 음주 습관 (`NONE` / `MODERATE` / `HEAVY`) |
| `created_at` | DATETIME(6) | AUTO | - |
| `updated_at` | DATETIME(6) | AUTO | - |

### HealthProfileHistory — 테이블: `health_profile_histories`

프로필 변경 시마다 스냅샷을 기록한다. 최대 12개월치 이력을 유지한다.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | BIGINT | PK | - |
| `health_profile_id` | BIGINT | FK → health_profiles(id) CASCADE | 원본 프로필 |
| `snapshot` | JSON | NOT NULL | 변경 시점의 프로필 전체 스냅샷 |
| `changed_by` | ENUM | NOT NULL | 변경 주체 (`USER` / `SYSTEM` / `ADMIN`) |
| `created_at` | DATETIME(6) | AUTO | 변경 시각 (이력 레코드는 불변) |

---

## 4. MedicalDocument / OCRResult

**파일:** `app/models/medical_documents.py`

### MedicalDocument — 테이블: `medical_documents`

사용자가 업로드한 의료 문서 원본 정보. 최대 10 MB, AES-256 암호화는 서비스 레이어에서 처리.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | BIGINT | PK | - |
| `user_id` | BIGINT | FK → users(id) CASCADE | 소유 사용자 |
| `document_type` | ENUM | NOT NULL | 문서 종류 (`PRESCRIPTION` / `MEDICINE_LABEL` / `DISCHARGE_NOTICE` / `HEALTH_CHECK`) |
| `file_path` | VARCHAR(512) | NOT NULL | 파일 저장 경로 (S3 key 등) |
| `file_format` | ENUM | NOT NULL | `PNG` / `JPG` / `PDF` |
| `file_size` | INT | NOT NULL | 파일 크기 (bytes, 서비스 레이어에서 ≤ 10 MB 검증) |
| `upload_status` | ENUM | DEFAULT `PENDING` | `PENDING` / `PROCESSING` / `SUCCESS` / `FAILED` |
| `confidence_score` | FLOAT | NULL | OCR 신뢰도 (0~100), OCR 완료 후 설정 |
| `is_verified` | BOOLEAN | DEFAULT FALSE | 사용자 내용 확인 여부 |
| `processed_at` | DATETIME(6) | NULL | OCR 처리 완료 시각 |
| `created_at` | DATETIME(6) | AUTO | - |
| `updated_at` | DATETIME(6) | AUTO | - |

### OCRResult — 테이블: `ocr_results`

문서에서 추출한 OCR 결과. `extracted_text`는 앱 레이어에서 AES-256으로 암호화하여 저장.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | BIGINT | PK | - |
| `document_id` | BIGINT | FK → medical_documents(id) CASCADE | 원본 문서 |
| `extracted_text` | LONGTEXT | NOT NULL | 추출 원문 (AES-256 암호화) |
| `structured_data` | JSON | NOT NULL | 구조화 데이터 (약물명, 진단, 용량 등) |
| `important_fields` | JSON | NOT NULL | 주요 필드 하이라이트 |
| `masked_pii` | BOOLEAN | DEFAULT FALSE | 개인정보 마스킹 처리 여부 |
| `created_at` | DATETIME(6) | AUTO | - |
| `updated_at` | DATETIME(6) | AUTO | - |

---

## 5. Medication

**파일:** `app/models/medications.py` | **테이블:** `medications`

처방전에서 추출하거나 사용자가 직접 입력한 약물 정보. `document_id`는 OCR 연동 시에만 설정되며 NULL 허용.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | BIGINT | PK | - |
| `user_id` | BIGINT | FK → users(id) CASCADE | 소유 사용자 |
| `document_id` | BIGINT | FK → medical_documents(id) SET NULL, NULL | 출처 문서 (수동 입력 시 NULL) |
| `medication_name` | VARCHAR(200) | NOT NULL | 약물명 |
| `dosage` | VARCHAR(100) | NOT NULL | 용량 (예: "500mg") |
| `frequency` | VARCHAR(100) | NOT NULL | 복용 빈도 (예: "하루 2회") |
| `duration` | VARCHAR(100) | NOT NULL | 복용 기간 (예: "7일") |
| `start_date` | DATE | NULL | 복용 시작일 |
| `end_date` | DATE | NULL | 복용 종료일 |
| `side_effects` | LONGTEXT | NULL | 부작용 설명 |
| `precautions` | LONGTEXT | NULL | 복용 주의사항 |
| `interaction_warnings` | LONGTEXT | NULL | 약물 상호작용 경고 |
| `created_at` | DATETIME(6) | AUTO | - |
| `updated_at` | DATETIME(6) | AUTO | - |

---

## 6. HealthGuidance

**파일:** `app/models/health_guidances.py` | **테이블:** `health_guidances`

LLM이 생성한 맞춤형 건강 안내. `health_profile_id`는 프로필 삭제 시 SET NULL 처리되어 안내 기록은 보존된다.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | BIGINT | PK | - |
| `user_id` | BIGINT | FK → users(id) CASCADE | 소유 사용자 |
| `health_profile_id` | BIGINT | FK → health_profiles(id) SET NULL, NULL | 생성 기준 건강 프로필 |
| `guidance_type` | ENUM | NOT NULL | `MEDICATION_GUIDE` / `LIFESTYLE_GUIDE` / `DIETARY_GUIDE` |
| `content` | LONGTEXT | NOT NULL | LLM 생성 안내 본문 |
| `ai_confidence` | FLOAT | NULL | AI 신뢰도 점수 |
| `requires_expert_review` | BOOLEAN | DEFAULT FALSE | 전문가 검토 필요 여부 |
| `verification_status` | ENUM | DEFAULT `PENDING` | `PENDING` / `VERIFIED` / `FLAGGED` |
| `created_at` | DATETIME(6) | AUTO | - |
| `updated_at` | DATETIME(6) | AUTO | - |

---

## Enum 목록

| Enum 클래스 | 값 | 파일 |
|-------------|-----|------|
| `Gender` | `MALE`, `FEMALE` | `users.py` |
| `MessageRole` | `USER`, `ASSISTANT` | `chats.py` |
| `ExerciseHabit` | `REGULAR`, `IRREGULAR`, `NONE` | `health_profiles.py` |
| `AlcoholHabit` | `NONE`, `MODERATE`, `HEAVY` | `health_profiles.py` |
| `ProfileChangedBy` | `USER`, `SYSTEM`, `ADMIN` | `health_profiles.py` |
| `DocumentType` | `PRESCRIPTION`, `MEDICINE_LABEL`, `DISCHARGE_NOTICE`, `HEALTH_CHECK` | `medical_documents.py` |
| `FileFormat` | `PNG`, `JPG`, `PDF` | `medical_documents.py` |
| `UploadStatus` | `PENDING`, `PROCESSING`, `SUCCESS`, `FAILED` | `medical_documents.py` |
| `GuidanceType` | `MEDICATION_GUIDE`, `LIFESTYLE_GUIDE`, `DIETARY_GUIDE` | `health_guidances.py` |
| `VerificationStatus` | `PENDING`, `VERIFIED`, `FLAGGED` | `health_guidances.py` |

---

## 마이그레이션

```bash
# 새 마이그레이션 파일 생성
aerich migrate --name add_health_models

# DB에 적용
aerich upgrade
```

생성 예상 테이블: `health_profiles`, `health_profile_histories`, `medical_documents`, `ocr_results`, `medications`, `health_guidances`
