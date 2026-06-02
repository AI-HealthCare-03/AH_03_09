# MediFind Bot — 프로젝트 문서

> **작성 기준**: 20년차 의료 웹 개발자 관점
> **프로젝트**: 카카오 OAuth 기반 의료 정보 AI 챗봇
> **스택**: FastAPI · Supabase · Kakao OAuth · GPT-4o-mini · Next.js
> **브랜치**: `feature/chatbot` (from `main`)
> **최종 업데이트**: 2026-05-14

---

## 목차

1. [PDCA — Plan · Do · Check · Act](#1-pdca)
2. [E-O — 자동수정·자가최적화 루프](#2-e-o)
3. [Pipeline — CI/CD 파이프라인](#3-pipeline)
4. [Deploy — 배포 절차](#4-deploy)

---

## 1. PDCA

### Plan — 설계 및 기술 스택 결정

| 항목 | 결정 사항 | 근거 |
|------|-----------|------|
| **목표** | 카카오 로그인 기반 의료 정보 AI 챗봇 SaaS | 국내 사용자 최적화 |
| **인증** | Kakao OAuth 2.0 + JWT (Access 60분 / Refresh 14일) | 소셜 로그인 UX + 보안 토큰 분리 |
| **AI 모델** | GPT-4o-mini | 비용 효율 × 의료 정보 품질 최적 균형 |
| **DB** | Supabase (PostgreSQL) | BaaS 관리형 서비스, 빠른 프로토타이핑 |
| **백엔드** | FastAPI 0.128+ / Python 3.13 / uv | 비동기 고성능, 타입 안전성 |
| **프론트엔드** | Next.js 14 App Router / TypeScript / Tailwind CSS | SEO 대응, 서버 컴포넌트 |
| **인프라** | Docker Compose → AWS EC2 + Nginx + Let's Encrypt | 컨테이너 이식성 + 무중단 배포 |
| **브랜치 전략** | `main` → `feature/chatbot` → PR 머지 | GitFlow 경량화 |

#### DB 스키마 (Supabase SQL Editor에서 실행)

```sql
-- 사용자 테이블 (카카오 ID 기준)
CREATE TABLE users (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  kakao_id      VARCHAR      UNIQUE NOT NULL,
  email         VARCHAR,
  nickname      VARCHAR      NOT NULL,
  profile_image VARCHAR,
  created_at    TIMESTAMPTZ  DEFAULT NOW()
);

-- 대화 세션 테이블
CREATE TABLE conversations (
  id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID         REFERENCES users(id) ON DELETE CASCADE,
  title      VARCHAR      DEFAULT '새 대화',
  created_at TIMESTAMPTZ  DEFAULT NOW()
);

-- 메시지 테이블
CREATE TABLE messages (
  id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID         REFERENCES conversations(id) ON DELETE CASCADE,
  role            VARCHAR      NOT NULL CHECK (role IN ('user', 'assistant')),
  content         TEXT         NOT NULL,
  created_at      TIMESTAMPTZ  DEFAULT NOW()
);

-- 인덱스 (조회 성능)
CREATE INDEX idx_conversations_user_id  ON conversations(user_id);
CREATE INDEX idx_messages_conv_id       ON messages(conversation_id);
CREATE INDEX idx_messages_created_at    ON messages(created_at);
```

#### API 설계 (9개 엔드포인트)

| Method | Endpoint | 설명 | 인증 |
|--------|----------|------|------|
| GET | `/api/v1/auth/kakao/login` | 카카오 인증 URL 반환 | ✗ |
| POST | `/api/v1/auth/kakao/callback?code=` | OAuth 콜백 → JWT 발급 | ✗ |
| GET | `/api/v1/auth/token/refresh` | 액세스 토큰 갱신 | 쿠키 |
| GET | `/api/v1/users/me` | 현재 사용자 정보 | JWT |
| POST | `/api/v1/chat/conversations` | 새 대화 생성 | JWT |
| GET | `/api/v1/chat/conversations` | 대화 목록 조회 | JWT |
| GET | `/api/v1/chat/conversations/{id}` | 대화 + 메시지 조회 | JWT |
| POST | `/api/v1/chat/conversations/{id}/messages` | 메시지 전송 + AI 응답 | JWT |
| DELETE | `/api/v1/chat/conversations/{id}` | 대화 삭제 | JWT |

---

### Do — 구현 완료 사항

#### 백엔드 (`feature/chatbot` 브랜치 커밋: `eb3ea6c`)

| 파일 | 역할 |
|------|------|
| `app/core/config.py` | Supabase/OpenAI/Kakao 환경변수 추가 |
| `app/core/db/supabase_client.py` | Supabase 클라이언트 싱글톤 |
| `app/models/users.py` | Tortoise ORM → Pydantic BaseModel |
| `app/services/auth.py` | Kakao OAuth 2.0 토큰 교환 + upsert |
| `app/services/chat.py` | GPT-4o-mini 호출, 히스토리 10개 컨텍스트 |
| `app/services/jwt.py` | Any 타입으로 User 의존 제거 |
| `app/repositories/user_repository.py` | Supabase upsert (kakao_id 기준) |
| `app/repositories/chat_repository.py` | conversations / messages CRUD |
| `app/apis/v1/auth_routers.py` | 카카오 로그인/콜백/토큰 갱신 라우터 |
| `app/apis/v1/chat_routers.py` | 챗봇 5개 엔드포인트 |
| `app/apis/v1/user_routers.py` | `/users/me` 단순화 |
| `app/dependencies/security.py` | Supabase 기반 JWT 인증 의존성 |
| `app/main.py` | CORS 미들웨어 추가, Tortoise 제거 |
| `docker-compose.yml` | MySQL 제거, Redis만 유지 |
| `pyproject.toml` | tortoise-orm/asyncmy/aerich 제거 → supabase/openai 추가 |

#### 프론트엔드 (`frontend/` 커밋: `692a1c4`)

| 파일 | 역할 |
|------|------|
| `app/page.tsx` | 카카오 로그인 버튼 페이지 |
| `app/auth/kakao/callback/page.tsx` | OAuth 콜백 처리 + localStorage JWT 저장 |
| `app/chat/page.tsx` | 사이드바 + 메시지 UI + 자동 대화 생성 |
| `components/ChatMessage.tsx` | user/assistant 메시지 버블 |
| `components/ChatInput.tsx` | 메시지 입력창 (Enter 전송, Shift+Enter 줄바꿈) |
| `components/ConversationSidebar.tsx` | 대화 목록 사이드바 |
| `lib/api.ts` | axios 인터셉터 (JWT 자동 갱신, 401 처리) |

---

### Check — 검토 및 발견된 이슈

| 우선순위 | 이슈 | 위치 | 영향 |
|----------|------|------|------|
| 🔴 HIGH | CI workflow에 MySQL 서비스 잔존 (Supabase 전환 미반영) | `.github/workflows/checks.yml` | 테스트 실패 |
| 🔴 HIGH | `feature/chatbot` 브랜치가 CI 트리거 목록에 없음 | `.github/workflows/checks.yml` | CI 미실행 |
| 🟡 MED | E-O 자가최적화 루프 미구현 | `app/services/chat.py` | 응답 품질 보장 불가 |
| 🟡 MED | 의료 응답 안전성 검증 없음 (응급 상황 미감지) | `app/services/chat.py` | 의료법·안전 리스크 |
| 🟡 MED | 테스트 코드 미작성 | `app/tests/` | 회귀 감지 불가 |
| 🟡 MED | Rate Limiting 없음 | `app/main.py` | OpenAI 비용 노출 |
| 🟢 LOW | `envs/example.local.env`가 MySQL 기준 | `envs/` | 신규 개발자 혼동 |
| 🟢 LOW | `app/core/db/databases.py` 잔존 | `app/core/db/` | 코드 혼란 |

---

### Act — 개선 액션 아이템

> 다음 스프린트 우선순위 순

1. **[HIGH]** `.github/workflows/checks.yml` → MySQL 서비스 제거, `feature/*` 트리거 추가, GitHub Secrets에 Supabase/OpenAI 키 등록
2. **[HIGH]** `app/services/chat.py` → E-O 자가최적화 루프 구현 (아래 E-O 섹션 참조)
3. **[MED]** `app/tests/` → 카카오 콜백, 챗봇 응답 단위 테스트 작성 (pytest-asyncio)
4. **[MED]** `app/main.py` → `slowapi` 기반 Rate Limiting 추가 (IP당 분당 20회)
5. **[LOW]** `envs/example.local.env` → Supabase/Kakao/OpenAI 환경변수 템플릿 업데이트
6. **[LOW]** `app/core/db/databases.py` 파일 삭제

---

## 2. E-O

> **E-O (자동수정·자가최적화 루프)**: GPT-4o-mini 응답이 의료 AI 챗봇 안전 기준에
> 부합하는지 자동 평가하고, 기준 미달 시 프롬프트를 강화하여 재시도하는 루프.
> 의료 서비스의 특수성(환자 안전, 의료법)을 감안해 응답 품질을 보장한다.

### 루프 흐름도

```
사용자 입력 (content)
        │
        ▼
┌───────────────────────┐
│ [1] 입력 안전성 검사   │
│  위험 키워드 감지?     │
│  (자살/자해/극약 등)   │
└───────┬───────────────┘
        │ YES → 즉시 응급 안내 메시지 반환 (DB 저장 후 종료)
        │ NO ↓
        ▼
┌───────────────────────────────────────────┐
│ [2] E-O 재시도 루프 (최대 3회)            │
│                                           │
│  attempt=0: 기본 시스템 프롬프트          │
│  attempt=1: "더 안전하고 구체적으로" 강화  │
│  attempt=2: "정보 제공만, 진단 금지" 강화  │
│                                           │
│  ┌─────────────────────────────────────┐  │
│  │ GPT-4o-mini 호출                    │  │
│  │ (시스템 프롬프트 + 히스토리 10개)    │  │
│  └──────────────┬──────────────────────┘  │
│                 │                         │
│  ┌──────────────▼──────────────────────┐  │
│  │ [3] 응답 품질 자동 평가              │  │
│  │  ✓ 길이 ≥ 20자                      │  │
│  │  ✓ 월권 발언 없음 (진단/처방 금지)  │  │
│  │  ✓ 비어있지 않음                    │  │
│  └──────────────┬──────────────────────┘  │
│                 │                         │
│           PASS ─┼─ FAIL → 다음 attempt    │
└─────────────────┼─────────────────────────┘
                  │ PASS
                  ▼
        DB 저장 후 사용자에게 반환
                  │
        3회 초과 FAIL → 안전 폴백 반환
```

### 구현 상수 및 설정

```python
# app/services/chat.py 에 추가

DANGER_KEYWORDS = [
    "자살", "자해", "독약", "극약", "과다복용",
    "수면제 다량", "농약 먹으면", "죽고 싶어"
]

MEDICAL_OVERREACH = [
    "진단해드리겠습니다", "처방해드리겠습니다",
    "치료해드릴게요", "이 약을 드세요"
]

EMERGENCY_RESPONSE = (
    "⚠️ 응급 상황이 의심됩니다. "
    "즉시 119에 전화하거나 가까운 응급실을 방문해 주세요. "
    "생명이 위험한 상황에서는 전문 의료진의 도움이 필요합니다."
)

SAFE_FALLBACK = (
    "죄송합니다, 현재 적절한 의료 정보를 제공하기 어렵습니다. "
    "증상이 지속되거나 심각하다면 반드시 전문의를 방문하시거나 "
    "응급 시 119에 연락하세요."
)

MAX_RETRY = 3
MIN_RESPONSE_LENGTH = 20

RETRY_PROMPT_SUFFIX = [
    "",  # attempt 0: 기본
    "\n\n반드시 안전하고 구체적인 의료 정보만 제공하세요.",   # attempt 1
    "\n\n정보 제공에만 집중하고 진단이나 처방은 절대 하지 마세요.",  # attempt 2
]
```

### 개선된 `send_message` 구현 (수도코드)

```python
def send_message(self, conversation_id: str, user_id: str, content: str) -> dict:
    conv = self.repo.get_conversation(conversation_id, user_id)
    if not conv:
        raise HTTPException(404, "대화를 찾을 수 없습니다.")

    # [1] 입력 안전성 검사
    if any(kw in content for kw in DANGER_KEYWORDS):
        msg = self.repo.create_message(conversation_id, "assistant", EMERGENCY_RESPONSE)
        return msg

    # user 메시지 저장
    self.repo.create_message(conversation_id, "user", content)
    history = self.repo.get_messages(conversation_id)

    # [2~3] E-O 재시도 루프
    for attempt in range(MAX_RETRY):
        system_content = SYSTEM_PROMPT + RETRY_PROMPT_SUFFIX[attempt]
        messages = [{"role": "system", "content": system_content}]
        messages += [{"role": m["role"], "content": m["content"]} for m in history[-10:]]

        completion = _openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        response_text = completion.choices[0].message.content or ""

        # [3] 품질 평가
        if (
            len(response_text) >= MIN_RESPONSE_LENGTH
            and not any(kw in response_text for kw in MEDICAL_OVERREACH)
        ):
            return self.repo.create_message(conversation_id, "assistant", response_text)

    # 3회 초과 → 안전 폴백
    return self.repo.create_message(conversation_id, "assistant", SAFE_FALLBACK)
```

### E-O 루프 성능 지표 (목표값)

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| 1회 통과율 | ≥ 90% | 재시도 없이 PASS된 비율 |
| 응급 감지율 | 100% | 위험 키워드 포함 메시지 감지 비율 |
| 평균 응답 시간 | ≤ 5초 | 1회 시도 기준 |
| 폴백 발생율 | ≤ 1% | 3회 초과 실패 비율 |

---

## 3. Pipeline

### 현재 파이프라인 구조

```
Push / PR
    │
    ├─ main, develop, release/*, hotfix/*   ← ⚠️ feature/* 없음
    │
    ▼
GitHub Actions (.github/workflows/checks.yml)
    │
    ├─ [Job: lint]
    │   ├─ Ruff check (린팅)
    │   └─ Ruff format --check (포매팅)
    │
    └─ [Job: test]
        ├─ MySQL 8.0 서비스 기동  ← ⚠️ Supabase 전환 후 불필요
        ├─ pytest 실행
        └─ coverage 리포트
```

### 개선된 파이프라인 (`checks.yml` 수정 내용)

```yaml
name: ci

on:
  push:
    branches:
      - main
      - develop
      - 'feature/*'      # ← 추가
      - 'release/*'
      - 'hotfix/*'
  pull_request:
    branches:
      - main
      - develop

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format . --check

  test:
    runs-on: ubuntu-latest
    # services: mysql 블록 전체 삭제
    env:
      SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
      SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      KAKAO_CLIENT_ID: ${{ secrets.KAKAO_CLIENT_ID }}
      KAKAO_CLIENT_SECRET: ${{ secrets.KAKAO_CLIENT_SECRET }}
      SECRET_KEY: ${{ secrets.SECRET_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: uv sync --group app --frozen
      - name: Run Tests with Coverage
        run: |
          uv run coverage run -m pytest app
          uv run coverage report -m
```

### 전체 파이프라인 흐름도

```
개발자 로컬 작업
      │
      │  ./scripts/ci/code_fommatting.sh  (Ruff 자동 수정)
      │  ./scripts/ci/check_mypy.sh       (타입 체크)
      │  ./scripts/ci/run_test.sh         (pytest + coverage)
      │
      ▼
git push origin feature/chatbot
      │
      ▼
GitHub Actions 트리거
      │
  ┌───┴──────────────────────┐
  │                          │
[lint Job]               [test Job]
  Ruff check               pytest
  Ruff format --check      coverage ≥ 70%
  │                          │
  └──────────┬───────────────┘
             │ 모두 PASS
             ▼
        PR 생성 → 코드 리뷰 → main 머지
             │
             ▼
     [수동] deployment.sh 실행
             │
      ┌──────┴───────────────────┐
      │                          │
  Docker 빌드              EC2 배포
  Docker Hub 푸시          docker compose up -d
      │                          │
      └──────────┬───────────────┘
                 ▼
           배포 완료 ✅
```

### GitHub Secrets 설정 목록

> Settings → Secrets and variables → Actions에서 등록

| Secret 이름 | 설명 |
|-------------|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_SERVICE_KEY` | Supabase service_role 키 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `KAKAO_CLIENT_ID` | 카카오 REST API 키 |
| `KAKAO_CLIENT_SECRET` | 카카오 클라이언트 시크릿 |
| `SECRET_KEY` | JWT 서명용 시크릿 키 |

---

## 4. Deploy

### 4-1. 사전 준비 — 외부 서비스 설정

#### ① Supabase 프로젝트 설정

```
1. https://supabase.com → New Project 생성
2. SQL Editor → 위 PDCA > Plan 섹션의 CREATE TABLE 3개 실행
3. Settings → API:
   - Project URL  → SUPABASE_URL
   - service_role → SUPABASE_SERVICE_KEY
4. .env 파일에 입력
```

#### ② 카카오 개발자 콘솔 설정

```
1. https://developers.kakao.com → 내 애플리케이션 → 앱 추가
2. 제품 설정 → 카카오 로그인 → 활성화
3. Redirect URI 등록:
   - 로컬:  http://localhost:3000/auth/kakao/callback
   - 운영:  https://your-domain.com/auth/kakao/callback
4. 동의항목:
   - 닉네임 (필수)
   - 프로필 사진 (선택)
   - 카카오계정(이메일) (선택)
5. 앱 키 → REST API 키  → KAKAO_CLIENT_ID
   보안 → Client Secret  → KAKAO_CLIENT_SECRET
```

#### ③ OpenAI API 키 발급

```
1. https://platform.openai.com → API Keys → Create new secret key
2. .env 파일에 OPENAI_API_KEY 입력
3. 사용량 한도 설정 권장 (월 $50 이하)
```

---

### 4-2. 로컬 개발 환경 실행

```bash
# ─── 백엔드 (AI_HealthCare_Final_Project_Template/) ───

# 1. 환경변수 설정
cp envs/example.local.env .env
# .env 파일에서 실제 값 입력 (SUPABASE_URL, OPENAI_API_KEY 등)

# 2. Redis만 실행 (MySQL 불필요)
docker compose up redis -d

# 3. 의존성 설치
uv sync --group app

# 4. 서버 실행
uv run uvicorn app.main:app --reload --port 8000

# Swagger UI: http://localhost:8000/api/docs


# ─── 프론트엔드 (frontend/) ───

# 1. 환경변수 설정
# .env.local 파일에서 값 입력
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" >> .env.local
echo "NEXT_PUBLIC_KAKAO_CLIENT_ID=your-kakao-client-id" >> .env.local

# 2. 의존성 설치
npm install

# 3. 개발 서버 실행
npm run dev
# 브라우저: http://localhost:3000
```

---

### 4-3. Docker 이미지 빌드 및 EC2 배포

```bash
# 프로젝트 루트에서 실행
./scripts/deployment.sh
```

**대화형 입력 순서:**

```
Docker Hub 사용자명:     your-dockerhub-username
Docker Hub 비밀번호:     your-access-token (PAT)
Docker Repository:       medifind-bot
배포 대상 선택:          1  (fastapi만 선택)
FastAPI 버전:            v1.0.1
SSH 키 파일명:           medifind_key.pem
EC2 IP:                  x.x.x.x
HTTP/HTTPS 여부:         1 (최초 HTTP, 이후 2로 변경)
```

**스크립트 내부 동작:**
```
1. Docker 로그인
2. linux/amd64 플랫폼으로 이미지 빌드
3. Docker Hub에 push
4. EC2로 SSH 접속:
   - .env 파일 SCP 복사
   - nginx.conf 파일 SCP 복사
   - docker compose up -d --pull always fastapi
   - docker image prune -af (이전 이미지 정리)
```

---

### 4-4. HTTPS 설정 (최초 1회)

```bash
./scripts/certbot.sh
```

**대화형 입력:**
```
도메인:       api.medifind.kr
이메일:       admin@medifind.kr
SSH 키 파일: medifind_key.pem
EC2 IP:      x.x.x.x
HTTPS 즉시 적용: Y
```

**스크립트 내부 동작:**
```
1. prod_http.conf의 server_name을 도메인으로 자동 수정
2. EC2에 SCP 업로드
3. Nginx 컨테이너 실행
4. Certbot으로 Let's Encrypt 인증서 발급 (webroot 방식)
5. prod_https.conf에 도메인 및 인증서 경로 자동 수정
6. HTTPS Nginx로 재시작
7. Certbot 자동갱신 컨테이너 실행
```

---

### 4-5. 환경변수 전체 목록

```env
# ─── 공통 ───
ENV=local                          # local | dev | prod
SECRET_KEY=강력한-랜덤-문자열-32자이상
COOKIE_DOMAIN=localhost            # 운영: your-domain.com

# ─── Supabase ───
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiI...

# ─── OpenAI ───
OPENAI_API_KEY=sk-proj-...

# ─── Kakao OAuth ───
KAKAO_CLIENT_ID=카카오-REST-API-키
KAKAO_CLIENT_SECRET=카카오-클라이언트-시크릿
KAKAO_REDIRECT_URI=http://localhost:3000/auth/kakao/callback

# ─── Frontend ───
FRONTEND_URL=http://localhost:3000  # 운영: https://your-domain.com

# ─── JWT ───
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_MINUTES=20160  # 14일

# ─── Docker (빌드 시만 사용) ───
DOCKER_USER=dockerhub-username
DOCKER_REPOSITORY=medifind-bot
APP_VERSION=v1.0.0
AI_WORKER_VERSION=v1.0.0
```

---

### 4-6. 프로덕션 아키텍처

```
사용자 브라우저 (Next.js: Vercel 또는 별도 EC2)
        │
        │ HTTPS 443
        ▼
┌──────────────────────────────────────────┐
│              AWS EC2 인스턴스             │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │     Nginx (Port 80 / 443)          │  │
│  │  - HTTP → HTTPS 리다이렉트         │  │
│  │  - /api/* → FastAPI:8000           │  │
│  │  - /.well-known/* → Certbot        │  │
│  └──────────────┬─────────────────────┘  │
│                 │                        │
│  ┌──────────────▼─────────────────────┐  │
│  │    FastAPI (Docker, Port 8000)      │  │
│  │    workers=3 (uvicorn)             │  │
│  └──────┬──────────────┬──────────────┘  │
│         │              │                 │
│  ┌──────▼──────┐       │                 │
│  │   Redis     │       │                 │
│  │ (JWT 캐시)  │       │                 │
│  └─────────────┘       │                 │
└────────────────────────┼─────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
   ┌──────▼──────┐              ┌───────▼──────┐
   │  Supabase   │              │    OpenAI    │
   │(PostgreSQL) │              │  GPT-4o-mini │
   │ [외부 SaaS] │              │  [외부 API]  │
   └─────────────┘              └──────────────┘
```

---

### 4-7. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `SUPABASE_URL` 미설정 에러 | `.env` 값 누락 | `.env`에 실제 값 입력 확인 |
| 카카오 로그인 실패 | Redirect URI 불일치 | 카카오 개발자 콘솔 URI 재등록 |
| JWT 만료 오류 | Access Token 60분 초과 | `lib/api.ts` 인터셉터가 자동 갱신 |
| GPT 응답 없음 | OPENAI_API_KEY 잘못됨 | API 키 확인 및 크레딧 잔액 확인 |
| CORS 오류 | `FRONTEND_URL` 불일치 | `config.py`의 `FRONTEND_URL` 값 확인 |
| Docker 빌드 실패 | uv.lock 동기화 오류 | `uv lock --upgrade` 후 재빌드 |

---

*이 문서는 `feature/chatbot` 브랜치 기준으로 작성되었습니다.*
*프로덕션 배포 전 반드시 PDCA > Act 항목의 개선 사항을 적용하세요.*
