-- ============================================================
-- 컨테이너 최초 기동 시 자동 실행 (postgres_data 볼륨이 비어있을 때)
-- 전체 스키마 DDL: users, chat, ocr 도메인
-- ============================================================

-- 확장
-- 컨테이너 최초 기동 시 자동 실행: PostgreSQL 확장만 설치.
-- 테이블 스키마는 FastAPI 기동 시 Tortoise.generate_schemas() 가 자동으로 생성한다.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- users (Kakao OAuth 기반 최소 스키마)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    kakao_id       VARCHAR(50) UNIQUE NOT NULL,
    email          VARCHAR(200),
    nickname       VARCHAR(100) NOT NULL,
    profile_image  VARCHAR(500),
    location       VARCHAR(200),
    is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- chat (챗봇 파트)
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(200) NOT NULL DEFAULT '새 대화',
    created_at TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         BIGSERIAL   PRIMARY KEY,
    session_id UUID        NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role       VARCHAR(10) NOT NULL,   -- 'user' | 'assistant'
    content    TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- ocr_documents (업로드된 파일 메타데이터)
-- record_id: BIGSERIAL (API 응답용 정수 PK)
-- job_id:    UUID (비동기 처리 추적용)
-- ============================================================
CREATE TABLE IF NOT EXISTS ocr_documents (
    record_id         BIGSERIAL    PRIMARY KEY,
    job_id            UUID         NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    user_id           UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    s3_key            VARCHAR(500) NOT NULL,
    s3_bucket         VARCHAR(100) NOT NULL,
    file_hash         VARCHAR(64),                 -- SHA-256 중복 업로드 방지
    file_size         INTEGER      NOT NULL,        -- bytes
    mime_type         VARCHAR(50)  NOT NULL,        -- image/jpeg | image/png | application/pdf
    thumbnail_url     VARCHAR(500),                 -- 썸네일 S3 URL
    doc_type          VARCHAR(20),                  -- 'PRESCRIPTION' | 'MEDICATION_BAG' | 'UNKNOWN'
    ocr_status        VARCHAR(20)  NOT NULL DEFAULT 'PENDING',  -- 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
    issued_date       DATE,                         -- 처방전 발급일
    valid_until       DATE,                         -- 처방전 유효기간
    hospital_name     VARCHAR(200),                 -- 발급 병원명
    is_active         BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- ocr_results (Clova OCR API 원본 처리 결과)
-- ============================================================
CREATE TABLE IF NOT EXISTS ocr_results (
    id                  BIGSERIAL    PRIMARY KEY,
    document_id         BIGINT       NOT NULL REFERENCES ocr_documents(record_id) ON DELETE CASCADE,
    raw_text            TEXT,                        -- Clova OCR 원본 텍스트
    processed_text      TEXT,                        -- 후처리된 텍스트
    clova_request_id    VARCHAR(100),
    confidence_score    NUMERIC(5,2),                -- 0.00 ~ 100.00 (%)
    processing_time_ms  INTEGER,                     -- 성능 측정용 (REQ-OCR-029)
    is_user_edited      BOOLEAN      NOT NULL DEFAULT FALSE,  -- 사용자 직접 수정 여부
    error_message       TEXT,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- medications (파싱된 약물 정보 - REQ-OCR-010)
-- ============================================================
CREATE TABLE IF NOT EXISTS medications (
    id               BIGSERIAL    PRIMARY KEY,
    document_id      BIGINT       NOT NULL REFERENCES ocr_documents(record_id) ON DELETE CASCADE,
    medication_name  VARCHAR(200) NOT NULL,
    generic_name     VARCHAR(200),                   -- 성분명
    dosage           VARCHAR(100),                   -- 용량 (예: 500mg)
    frequency        VARCHAR(100),                   -- 복용 횟수 (예: 하루 3회)
    timing           VARCHAR(100),                   -- 복용 시점 (예: 식후 30분)
    duration_days    INTEGER,                        -- 복용 일수
    time_of_day      JSONB,                          -- {"morning": true, "afternoon": false, "evening": true, "bedtime": false}
    instructions     TEXT,                           -- 복약 지도 전문
    warnings         JSONB,                          -- 주의사항 배열
    confidence_score NUMERIC(5,2),                   -- OCR 파싱 신뢰도
    is_confirmed     BOOLEAN      NOT NULL DEFAULT FALSE,  -- REQ-OCR-017 confirm API
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- disease_codes (ICD-10 질병분류기호 - REQ-OCR-011)
-- ============================================================
CREATE TABLE IF NOT EXISTS disease_codes (
    id               BIGSERIAL    PRIMARY KEY,
    document_id      BIGINT       NOT NULL REFERENCES ocr_documents(record_id) ON DELETE CASCADE,
    icd10_code       VARCHAR(20)  NOT NULL,           -- 예: J00, J06.9
    disease_name     VARCHAR(200),                    -- 한국어 질병명
    is_primary       BOOLEAN      NOT NULL DEFAULT FALSE,  -- 주진단 여부
    confidence_score NUMERIC(5,2),
    is_confirmed     BOOLEAN      NOT NULL DEFAULT FALSE,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- ocr_corrections (사용자 수정 이력 - REQ-OCR-015)
-- ============================================================
CREATE TABLE IF NOT EXISTS ocr_corrections (
    id             BIGSERIAL    PRIMARY KEY,
    document_id    BIGINT       NOT NULL REFERENCES ocr_documents(record_id) ON DELETE CASCADE,
    field_name     VARCHAR(100) NOT NULL,             -- 수정된 필드명
    entity_type    VARCHAR(50)  NOT NULL,             -- 'medication' | 'disease_code' | 'document'
    entity_id      BIGINT,                            -- 수정된 entity의 PK
    original_value TEXT,
    corrected_value TEXT,
    corrected_by   UUID         NOT NULL REFERENCES users(id),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- ai_performance_metrics (AI 성능 측정 - REQ-OCR-029/030)
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_performance_metrics (
    id                    BIGSERIAL    PRIMARY KEY,
    document_id           BIGINT       REFERENCES ocr_documents(record_id) ON DELETE SET NULL,
    metric_type           VARCHAR(50)  NOT NULL,   -- 'OCR_ACCURACY' | 'PARSE_ACCURACY' | 'LATENCY'
    metric_value          NUMERIC(10,4) NOT NULL,
    baseline_value        NUMERIC(10,4),
    measured_at           TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    additional_info       JSONB
);

-- ============================================================
-- 인덱스
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_ocr_documents_user_id   ON ocr_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_ocr_documents_job_id    ON ocr_documents(job_id);
CREATE INDEX IF NOT EXISTS idx_ocr_documents_status    ON ocr_documents(ocr_status);
CREATE INDEX IF NOT EXISTS idx_ocr_documents_is_active ON ocr_documents(is_active);
CREATE INDEX IF NOT EXISTS idx_ocr_results_document    ON ocr_results(document_id);
CREATE INDEX IF NOT EXISTS idx_medications_document    ON medications(document_id);
CREATE INDEX IF NOT EXISTS idx_disease_codes_document  ON disease_codes(document_id);
CREATE INDEX IF NOT EXISTS idx_ocr_corrections_doc     ON ocr_corrections(document_id);
CREATE INDEX IF NOT EXISTS idx_ai_metrics_document     ON ai_performance_metrics(document_id);
