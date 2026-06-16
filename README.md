# Medi-Mate — AI 기반 복약 가이드 & 건강 챗봇

> 처방전·약봉투를 찍으면, 복약 가이드까지

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

<!-- 📌 이미지 권장 위치 ①: 서비스 메인 화면 스크린샷 (가로 전체 배너) -->
<!-- 예: ![Medi-Mate 메인 화면](docs/images/hero.png) -->

---

## 📋 목차

- [프로젝트 소개](#-프로젝트-소개)
- [주요 기능](#-주요-기능)
- [기술 스택](#-기술-스택)
- [시스템 아키텍처](#-시스템-아키텍처)
- [OCR 파이프라인](#-ocr-파이프라인)
- [디렉토리 구조](#-디렉토리-구조)
- [로컬 환경 설정](#-로컬-환경-설정)
- [환경변수](#-환경변수)
- [배포](#-배포)
- [팀원](#-팀원)
- [관련 문서](#-관련-문서)

---

## 🏥 프로젝트 소개

Medi-Mate는 처방전·약봉투 사진을 AI로 분석하여 복약 정보를 자동 추출하고, 개인 맞춤형 복약 가이드와 건강 챗봇을 제공하는 헬스케어 서비스입니다.

약 이름 하나하나를 직접 검색하지 않아도, 사진 한 장으로 복약 방법·주의사항·생활 가이드까지 한 번에 확인할 수 있습니다.

**배포 URL**: [https://mediai.kro.kr](https://mediai.kro.kr)

---

## ✨ 주요 기능

### 📄 처방전·약봉투 OCR 분석
- JPG·PNG·PDF 업로드 → Clova OCR + GPT 파싱 자동 처리
- 약물명·용량·복약횟수·기간·ICD-10 질병코드 자동 추출
- 식약처 43,143건 drug_master DB 매칭 및 신뢰도 표시 (3색 뱃지: ≥80% / 60~79% / <60%)
- 약물 정보 인라인 편집 (추가·수정·삭제), 전체 확인 후 가이드 생성

<!-- 📌 이미지 권장 위치 ②: OCR 결과 화면 스크린샷 (약물 목록, 신뢰도 뱃지) -->

### 💊 맞춤형 복약 가이드
- OCR 결과 확인 후 원클릭으로 가이드 생성 (비동기 처리)
- 복약·생활·식사·운동 4가지 유형별 가이드 제공
- 식약처 drug_master 용법·부작용·주의사항 데이터 주입
- 사용자 건강정보(나이대·성별·기저질환·생활습관)와 처방 내용 통합 반영

<!-- 📌 이미지 권장 위치 ③: 복약 가이드 화면 스크린샷 -->

### 🤖 건강 챗봇
- 처방전 기반 RAG — drug_master pgvector 코사인 유사도 검색으로 약물 상세 정보 주입
- Tool Calling 적용 — LLM이 필요한 데이터(약물 정보·건강 프로필·가이드)를 on-demand로 조회
- 5가지 질문 유형 분류 및 라우팅
- 위험 키워드 감지·욕설 필터링·의료 불확실성("전문가 확인 권장") 안전장치 적용

<!-- 📌 이미지 권장 위치 ④: 챗봇 화면 스크린샷 -->

### 👤 건강 프로필 관리
- 카카오 OAuth 로그인 (개인 개발자 비즈 앱)
- 성별·나이대·키·체중·혈압·기저질환·알레르기·복용약·생활습관 입력
- 건강정보 저장 시 `users` 테이블 동기화 → 챗봇 컨텍스트에 즉시 반영

---

## 🛠 기술 스택

| 분류 | 기술 |
|------|------|
| **Language** | Python 3.13, TypeScript |
| **Backend** | FastAPI, SQLAlchemy async |
| **Frontend** | React 18, Vite, Tailwind CSS v4, shadcn/ui, Framer Motion |
| **Database** | PostgreSQL 16 + pgvector |
| **Cache / Queue** | Redis pub/sub |
| **AI / OCR** | Clova OCR API, OpenAI GPT-4o, text-embedding-3-small |
| **Auth** | Kakao OAuth 2.0, PyJWT (HS256) |
| **Package Manager** | uv (Python), pnpm (Node) |
| **Container** | Docker Compose |
| **Infra** | AWS EC2 (t3.micro), Nginx, Let's Encrypt (SSL) |

---

## 🏗 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  사용자 (브라우저)                                            │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTPS (mediai.kro.kr)
┌───────────────────────▼─────────────────────────────────────┐
│  Nginx (리버스 프록시 · 80/443)                              │
│  ├─ /api/*  →  FastAPI (port 8000)                          │
│  └─ /*      →  Frontend / React (port 80, nginx 서빙)       │
└───────────┬─────────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────┐
│  FastAPI                                                     │
│  Router → Service → Repository → PostgreSQL 16              │
│                    ↓                                         │
│              Redis PUBLISH  ──────────────────────────────── ┤
│                                                              │
│  [동기 응답] 즉시 202 반환 (P95 < 500ms)                     │
└─────────────────────────────────────────────────────────────┘
            │ Redis SUBSCRIBE
┌───────────▼─────────────────────────────────────────────────┐
│  ai_worker (비동기 백그라운드)                               │
│  ├─ OCR 작업:   Clova OCR → doc_classifier → GPT 파싱       │
│  ├─ 가이드 작업: 건강정보 + 처방 데이터 → GPT-4o 생성         │
│  └─ 챗봇 작업:  Tool Calling → pgvector RAG → 스트리밍        │
└─────────────────────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────┐
│  PostgreSQL 16 + pgvector                                   │
│  ├─ ocr_documents / ocr_results / medications / disease_codes│
│  ├─ drug_master (43,143건 · 임베딩 1536차원)                 │
│  ├─ health_profiles / users                                 │
│  └─ chat_sessions / chat_messages / guides                  │
└─────────────────────────────────────────────────────────────┘
```

<!-- 📌 이미지 권장 위치 ⑤: 시스템 아키텍처 다이어그램 (시각화) -->
<!-- 참고: docs/chatbot/chatbot-architecture.mmd, docs/system-design.md -->

---

## 🔄 OCR 파이프라인

### 처리 흐름

```
① 파일 업로드 (JPG · PNG · PDF, 최대 10MB)
   ↓
② FastAPI 유효성 검사
   · MIME + 확장자 이중 검증
   · PDF 2페이지 초과 → 422
   · SHA-256 해시 중복 감지 → 409
   · 일일 한도 초과 (20건/일) → 429
   ↓
③ 파일 저장 (로컬 /tmp/ocr_uploads/) + DB INSERT (PENDING)
   + Redis PUBLISH ocr:request:{job_id}
   → 즉시 202 Accepted 반환  ←── P95 < 500ms
   ↓
④ ai_worker 수신 (비동기)
   ↓
⑤ 이미지 전처리
   · JPG/PNG 8000px 초과 시 자동 리사이즈 (Pillow)
   ↓
⑥ Clova OCR API 호출
   · raw_text 추출 + 블록별 confidence_score 평균
   · 인식 실패 (QR코드·이상 파일) → IMAGE_UNRECOGNIZABLE
   · PDF 해상도 초과 → PDF_RESOLUTION_EXCEEDED
   ↓
⑦ 문서 유형 분류
   · 1차: 키워드 점수 기반 (처방전·약봉투 특징어)
   · 2차: GPT-4o 폴백 분류
   → PRESCRIPTION / DRUG_BAG / OTHER
   ↓
⑧ GPT-4o 파싱 (temperature=0, json_object)
   · 텍스트 전처리: 영수증·행정정보 노이즈 제거, ICD-10 코드 복원
   · 약물명·용량·복약횟수·기간·복약시기·경고 추출
   · 질병분류기호 ICD-10 추출 (처방전만)
   ↓
⑨ drug_master 매칭 (식약처 43,143건)
   · LIKE + word_similarity 랭킹
   · 성분명 검증으로 오매칭 방지
   · is_db_matched = true/false 표기
   ↓
⑩ 결과 저장
   · ocr_results: raw_text + processed_text(PII 마스킹) + confidence_score
   · medications: 약물 목록
   · disease_codes: 질병분류기호
   · ai_performance_metrics: 처리 시간(LATENCY) 기록
   ↓
⑪ 상태 → DONE / FAILED
   · confidence_score < 0.7 → retake_recommended = true
```

### 성능 지표

| 지표 | 측정값 | 기준 |
|------|--------|------|
| API 응답 P95 Latency | **< 500ms** | FastAPI 엔드포인트 |
| OCR 파이프라인 평균 처리 시간 | **1,601ms** | ai_worker (외부 API 포함) |
| OCR 파이프라인 P95 처리 시간 | **3,638ms** | ai_worker |
| 처방전 평균 신뢰도 | **88.38%** | n=13건 |
| 약봉투 평균 신뢰도 | **85.86%** | n=7건 |

> 상세 데이터 및 재현 방법 → [`docs/ocr/performance-report.md`](docs/ocr/performance-report.md)  
> 전체 플로우차트 (상세) → [`docs/ocr/ocr_workflow.mmd`](docs/ocr/ocr_workflow.mmd)  
> 발표용 간략 플로우차트 → [`docs/ocr/ocr_pipeline_simple.mmd`](docs/ocr/ocr_pipeline_simple.mmd)

<!-- 📌 이미지 권장 위치 ⑥: ocr_pipeline_simple.mmd 렌더링 결과 이미지 -->

---

## 📁 디렉토리 구조

```
AH_03_09/
├── app/                              # FastAPI 백엔드
│   ├── apis/v1/
│   │   ├── ocr/
│   │   │   └── ocr_routers.py        # OCR 업로드·상태·결과·약물·가이드 확인
│   │   ├── auth_routers.py           # 카카오 OAuth, 토큰 갱신, 로그아웃
│   │   ├── chat_routers.py           # 챗봇 세션·메시지·WebSocket
│   │   ├── guide_routers.py          # 가이드 생성·조회·피드백
│   │   ├── health_profile_routers.py # 건강정보 CRUD
│   │   └── user_routers.py           # 사용자 조회·온보딩·탈퇴
│   ├── models/
│   │   ├── users.py                  # 사용자 (카카오 정보 + 건강 맥락)
│   │   ├── ocr/ocr_document.py       # OCR 문서·결과·약물·질병코드
│   │   ├── health_profiles.py        # 건강 프로필 + 이력
│   │   ├── drug_master.py            # 식약처 의약품 DB (43,143건)
│   │   ├── guides.py                 # 복약 가이드
│   │   └── chat.py                   # 챗봇 세션·메시지
│   ├── services/
│   │   ├── ocr/document_service.py   # OCR 비즈니스 로직
│   │   ├── guides.py                 # 가이드 생성·상태 관리 (Redis)
│   │   ├── chat.py                   # 챗봇 컨텍스트 구성·RAG
│   │   ├── health_profiles.py        # 건강정보 CRUD + 이력 기록
│   │   ├── rag.py                    # pgvector 코사인 유사도 검색
│   │   └── auth.py                   # JWT 발급·갱신, 카카오 토큰 교환
│   ├── repositories/
│   │   ├── ocr/document_repository.py
│   │   ├── user_repository.py
│   │   └── health_profile_repository.py
│   ├── dtos/                         # Pydantic 요청·응답 스키마
│   ├── core/
│   │   ├── db/sqlalchemy_client.py   # async 세션 팩토리
│   │   ├── jwt/                      # AccessToken·RefreshToken 발급
│   │   └── cleanup.py               # 소프트삭제 30일 후 하드삭제 루프
│   └── dependencies/security.py     # JWT 인증 의존성
│
├── ai_worker/                        # 비동기 AI 처리 워커 (Redis pub/sub)
│   ├── main.py                       # psubscribe 루프 (ocr·chat·guide)
│   ├── tasks/
│   │   ├── ocr_task.py               # Clova OCR + PII 마스킹 + 약물 정규화
│   │   ├── ocr_parser.py             # GPT-4o 파싱 프롬프트 + ICD-10 전처리
│   │   ├── doc_classifier.py         # 문서 유형 분류 (키워드 → GPT 폴백)
│   │   ├── guide_task.py             # 복약 가이드 생성 (4가지 유형)
│   │   └── chat_task.py              # 챗봇 스트리밍 응답
│   └── core/
│       ├── llm.py                    # LLM 프롬프트 & Tool Calling 정의
│       └── config.py                 # 환경변수 (OPENAI·CLOVA·DB·Redis)
│
├── frontend/                         # React 18 + Vite 프론트엔드
│   └── src/
│       ├── pages/
│       │   ├── ocr/
│       │   │   ├── Upload.tsx         # 파일 업로드 (드래그&드롭)
│       │   │   ├── UploadProcessing.tsx  # 상태 폴링·에러 분기
│       │   │   ├── UploadResult.tsx   # 결과 확인·약물 편집·가이드 생성
│       │   │   └── MyDocuments.tsx    # 문서 목록·필터·정렬
│       │   ├── HealthGuide.tsx        # 복약 가이드 표시·피드백
│       │   ├── HealthProfile.tsx      # 건강정보 조회·수정
│       │   ├── Home.tsx              # 홈 화면 (최근 문서·가이드 바로가기)
│       │   ├── Onboarding.tsx        # 의료정보 동의 + 건강정보 입력
│       │   ├── Profile.tsx           # 내 정보 (카카오·계정 관리)
│       │   └── chatbot/Chat.tsx      # 챗봇 UI (스트리밍)
│       ├── features/
│       │   ├── health-profile/       # 건강정보 폼 + Zod 스키마
│       │   └── landing/HeroSection.tsx
│       ├── hooks/
│       │   └── useDebounce.ts        # 약물 검색 디바운싱
│       └── lib/
│           ├── withAuthRetry.ts      # 401 자동 토큰 갱신
│           └── inputValidation.ts    # 비속어 필터·입력 가드레일
│
├── alembic/                          # DB 마이그레이션
│   └── versions/                     # 버전별 마이그레이션 파일
│
├── scripts/
│   ├── deployment.sh                 # 이미지 빌드·푸시·EC2 배포 자동화
│   ├── certbot.sh                    # Let's Encrypt SSL 인증서 발급
│   ├── generate_drug_embeddings.py   # drug_master 임베딩 생성 (1회성)
│   └── load_drug_master.py           # 식약처 CSV → drug_master 적재 (1회성)
│
├── infra/
│   ├── docker/docker-compose.prod.yml
│   └── nginx/
│       ├── prod_http.conf            # HTTP (80)
│       └── prod_https.conf           # HTTPS (443), SSL 설정
│
├── docs/
│   ├── ocr/
│   │   ├── ocr_workflow.mmd          # OCR 전체 상세 플로우차트
│   │   ├── ocr_pipeline_simple.mmd   # 발표용 간략 파이프라인
│   │   ├── performance-report.md     # P95 Latency·신뢰도·일관성 보고서
│   │   └── prompt-improvement-log.md # GPT 프롬프트 개선 이력 (v1~v11)
│   ├── chatbot/
│   │   ├── chatbot-flow.mmd          # 챗봇 처리 흐름
│   │   ├── chatbot-architecture.mmd  # 챗봇 아키텍처 다이어그램
│   │   └── system-flow.mmd           # 전체 시스템 흐름
│   ├── guide/guide-flow.mmd          # 가이드 생성 플로우
│   ├── system-design.md             # 전체 시스템 설계 문서
│   ├── dev_guide.md                 # 개발 환경 설정 가이드
│   ├── models.md                    # DB 모델 명세
│   └── backend_guidelines.md        # 백엔드 코딩 가이드라인
│
└── envs/
    ├── example.local.env             # 로컬 환경변수 템플릿
    └── example.prod.env              # 프로덕션 환경변수 템플릿
```

---

## 🚀 로컬 환경 설정

### 사전 요구사항

- Python 3.13+, [uv](https://docs.astral.sh/uv/)
- Node.js 20+, pnpm
- Docker Desktop

### 1. 저장소 클론

```bash
git clone https://github.com/AI-HealthCare-03/AH_03_09.git
cd AH_03_09
```

### 2. 환경변수 설정

```bash
cp envs/example.local.env envs/.local.env
# .local.env에 실제 값 입력 (카카오 키, OpenAI 키, Clova 키 등)
```

### 3. Docker 실행 (PostgreSQL + Redis)

```bash
docker compose up -d postgres redis
```

### 4. DB 마이그레이션

```bash
uv run alembic upgrade head
```

### 5. drug_master 데이터 적재 (최초 1회)

```bash
# 식약처 의약품 개요정보 CSV 파일 필요 (공공데이터 포털 또는 팀 내 보관본)
# 파일 크기 1.2GB 이상, .gitignore로 제외됨 (*.csv)
uv run python scripts/load_drug_master.py
```

### 6. 임베딩 생성 (최초 1회, 챗봇 RAG용)

```bash
# OpenAI text-embedding-3-small 사용, 약 $0.10 소요 (43,143건)
DB_HOST=localhost PYTHONPATH=. uv run python scripts/generate_drug_embeddings.py
```

### 7. ai_worker 실행

```bash
# 코드 변경 시 반드시 재빌드 필요 (볼륨 마운트 없음)
docker compose build ai-worker && docker compose up -d ai-worker
```

### 8. FastAPI 실행

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 9. 프론트엔드 실행

```bash
cd frontend
pnpm install
pnpm dev
# http://localhost:3000
```

---

## 🔑 환경변수

`envs/example.local.env` 및 `envs/example.prod.env` 참고.

| 변수 | 설명 |
|------|------|
| `KAKAO_CLIENT_ID` | 카카오 REST API 키 (개인 개발자 비즈 앱) |
| `KAKAO_REDIRECT_URI` | 카카오 Redirect URI |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `OPENAI_MODEL` | GPT 모델 (로컬: `gpt-4o-mini` / 배포: `gpt-4o`) |
| `CLOVA_OCR_INVOKE_URL` | Clova OCR Invoke URL (**`CLOVA_OCR_API_URL`** 아님 주의) |
| `CLOVA_OCR_SECRET_KEY` | Clova OCR Secret Key |
| `COOKIE_DOMAIN` | 쿠키 도메인 (로컬: `localhost` / 배포: `mediai.kro.kr`) |
| `VITE_API_BASE_URL` | 프론트엔드 API 기본 URL (끝 슬래시 없이) |

---

## 📦 배포

### 배포 환경

- **서버**: AWS EC2 t3.micro (서울 리전, ap-northeast-2)
- **도메인**: mediai.kro.kr (Let's Encrypt SSL, auto-certbot 90일 자동 갱신)
- **컨테이너**: Docker Compose (FastAPI · ai-worker · Frontend · Nginx · PostgreSQL · Redis)

### 배포 명령

```bash
bash scripts/deployment.sh
# 1) fastapi  2) ai_worker  3) frontend 중 선택하여 빌드·배포
# 버전 입력 시 envs/.prod.env 자동 업데이트
```

### 초기 배포 시 데이터 설정

```bash
# drug_master 임베딩 생성 (SSH 터널 방식 권장 — t3.micro OOM 방지)
ssh -i ~/.ssh/키파일.pem -L 15432:localhost:5432 ubuntu@EC2_IP -N -f
DB_HOST=localhost DB_PORT=15432 PYTHONPATH=. uv run python scripts/generate_drug_embeddings.py
```

### 모델 교체 (개발 완료 후, 재빌드 불필요)

```bash
# envs/.prod.env 수정 후:
scp -i ~/.ssh/키파일.pem envs/.prod.env ubuntu@EC2_IP:~/project/.env
ssh -i ~/.ssh/키파일.pem ubuntu@EC2_IP "cd project && docker compose up -d --no-deps fastapi ai-worker"
```

---

## 👥 팀원

| 이름 | 역할 | 담당 파트 |
|------|------|----------|
| **김민혁** (팀장) | BE · FE · 인프라 | OCR 전체 파이프라인, 건강프로필, 온보딩, 홈·프로필·내문서 페이지, AWS 배포·HTTPS 설정, CI/CD 스크립트 |
| **신영민** | BE · FE | 건강 챗봇 (RAG · Tool Calling · 스트리밍), 챗봇 UI, 욕설 필터링 |
| **윤지현** | BE · FE | 복약 가이드 생성 (LLM · 4유형), 가이드 목록·피드백 UI, LLM 정책 설계 |

---

## 📄 관련 문서

### OCR
| 문서 | 설명 |
|------|------|
| [`docs/ocr/ocr_workflow.mmd`](docs/ocr/ocr_workflow.mmd) | OCR 전체 상세 플로우차트 (6개 섹션) |
| [`docs/ocr/ocr_pipeline_simple.mmd`](docs/ocr/ocr_pipeline_simple.mmd) | 발표용 간략 파이프라인 |
| [`docs/ocr/performance-report.md`](docs/ocr/performance-report.md) | P95 Latency · 신뢰도 · 비동기 구조 성능 보고서 |
| [`docs/ocr/prompt-improvement-log.md`](docs/ocr/prompt-improvement-log.md) | GPT 파싱 프롬프트 개선 이력 (v1~v11) |

### 챗봇
| 문서 | 설명 |
|------|------|
| [`docs/chatbot/chatbot-flow.mmd`](docs/chatbot/chatbot-flow.mmd) | 챗봇 처리 흐름 (RAG · Tool Calling) |
| [`docs/chatbot/chatbot-architecture.mmd`](docs/chatbot/chatbot-architecture.mmd) | 챗봇 아키텍처 다이어그램 |
| [`docs/chatbot/system-flow.mmd`](docs/chatbot/system-flow.mmd) | 전체 시스템 흐름 |

### 가이드
| 문서 | 설명 |
|------|------|
| [`docs/guide/guide-flow.mmd`](docs/guide/guide-flow.mmd) | 가이드 생성 플로우 |
| [`docs/llm-guide-plan.md`](docs/llm-guide-plan.md) | LLM 가이드 설계 계획 |
| [`docs/llm-guide-policy.md`](docs/llm-guide-policy.md) | 가이드 생성 정책 및 룰 |

### 공통
| 문서 | 설명 |
|------|------|
| [`docs/system-design.md`](docs/system-design.md) | 전체 시스템 설계 문서 |
| [`docs/models.md`](docs/models.md) | DB 모델 명세 |
| [`docs/dev_guide.md`](docs/dev_guide.md) | 개발 환경 설정 가이드 |
| [`docs/backend_guidelines.md`](docs/backend_guidelines.md) | 백엔드 코딩 가이드라인 |
| [`docs/easy_summary_style_guide.md`](docs/easy_summary_style_guide.md) | 챗봇 응답 문체 가이드 |
