# MediFind Bot — 전체 구현 코드 레퍼런스

> FastAPI + PostgreSQL(PGvector + PostGIS) + Kakao OAuth + GPT-4o-mini + Next.js 14 기반 의료 정보 AI 챗봇  
> 브랜치: `feature/chatbot` | 최종 수정: 2026-05-14

---

## 목차

1. [프로젝트 아키텍처 개요](#1-프로젝트-아키텍처-개요)
2. [데이터베이스 스키마 (PostgreSQL + PGvector + PostGIS)](#2-데이터베이스-스키마-postgresql--pgvector--postgis)
3. [백엔드 전체 구현 코드](#3-백엔드-전체-구현-코드)
4. [E-O 자가최적화 루프 (핵심 구현)](#4-e-o-자가최적화-루프-핵심-구현)
5. [프론트엔드 전체 구현 코드](#5-프론트엔드-전체-구현-코드)
6. [CI/CD 및 테스트 코드](#6-cicd-및-테스트-코드)

---

## 1. 프로젝트 아키텍처 개요

### 기술 스택

| 레이어 | 기술 | 버전 |
|--------|------|------|
| 백엔드 프레임워크 | FastAPI | ≥0.128.0 |
| 런타임 | Python | 3.13 |
| 패키지 매니저 | uv | latest |
| 데이터베이스 | PostgreSQL 17 + PGvector + PostGIS | Self-hosted |
| AI 모델 | GPT-4o-mini | OpenAI API |
| 인증 | Kakao OAuth 2.0 + JWT (HS256) | — |
| 캐시 | Redis | alpine |
| 프론트엔드 | Next.js (App Router) | 16.2.6 |
| UI | Tailwind CSS | v4 |
| 언어 | TypeScript | ≥5 |
| 컨테이너 | Docker Compose | — |
| 배포 | AWS EC2 + Nginx + Let's Encrypt | — |

### 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자 브라우저                            │
│            Next.js 14 App Router (localhost:3000)               │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────────┐│
│  │ /        │  │ /auth/kakao/ │  │ /chat                      ││
│  │ LoginPage│  │ callback     │  │ ConversationSidebar + Chat  ││
│  └──────────┘  └──────────────┘  └────────────────────────────┘│
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API (axios + Bearer JWT)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI (localhost:8000)                       │
│                                                                 │
│  /api/v1/auth/*   →  AuthService  →  Kakao OAuth 2.0           │
│  /api/v1/users/*  →  UserService  →  UserRepository            │
│  /api/v1/chat/*   →  ChatService  →  ChatRepository            │
│                         (E-O Loop)                              │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
  ┌─────────┐      ┌──────────────┐   ┌──────────────┐
  │  Redis  │      │  PostgreSQL  │   │   OpenAI     │
  │  :6379  │      │    :5432     │   │  GPT-4o-mini │
  │JWT Cache│      │+PGvector     │   │              │
  └─────────┘      │+PostGIS      │   └──────────────┘
                   │users/convs/  │
                   │messages/     │
                   │hospitals     │
                   └──────────────┘
```

### 인증 플로우

```
1. 프론트엔드: 카카오 인증 URL로 리다이렉트
   → https://kauth.kakao.com/oauth/authorize?client_id=...&redirect_uri=...

2. 카카오: 인증 후 /auth/kakao/callback?code=AUTH_CODE 리다이렉트

3. 프론트엔드: code 파라미터 추출
   → POST /api/v1/auth/kakao/callback?code=AUTH_CODE

4. 백엔드:
   a. 카카오 토큰 교환 (kauth.kakao.com/oauth/token)
   b. 카카오 유저 정보 조회 (kapi.kakao.com/v2/user/me)
   c. PostgreSQL users 테이블 upsert (kakao_id 기준)
   d. JWT pair 발급 (access_token 60분 / refresh_token 14일)

5. 응답:
   - Body: { access_token: "eyJ..." }
   - Cookie: refresh_token (HttpOnly, SameSite=lax)

6. 프론트엔드: localStorage에 access_token 저장 → /chat 이동
```

### 채팅 플로우 (E-O 루프 포함)

```
사용자 입력
    │
    ▼
[1] 입력 안전성 검사
    ├─ DANGER_KEYWORDS 감지 → EMERGENCY_RESPONSE 즉시 반환
    └─ 통과 → [2]로 진행
    │
    ▼
[2] user 메시지 DB 저장 (PostgreSQL messages)
    │
    ▼
[3] 히스토리 조회 (최근 10개)
    │
    ▼
[4~6] E-O 재시도 루프 (MAX_RETRY=3)
    │   ┌──────────────────────────────────┐
    │   │ attempt=0: 기본 프롬프트          │
    │   │ attempt=1: 의료 면책 강화 추가    │
    │   │ attempt=2: 구체적 지침 강화 추가  │
    │   └──────────────────────────────────┘
    │         │
    │    GPT-4o-mini 호출
    │         │
    │   품질 평가 (QualityChecker)
    │   ├─ PASS → assistant 메시지 DB 저장 → 반환
    │   └─ FAIL → 다음 attempt
    │
    ▼ (3회 모두 실패)
SAFE_FALLBACK 반환
```

### 디렉토리 구조

```
Final-Project/
├── AI_HealthCare_Final_Project_Template/    # 백엔드 루트
│   ├── app/
│   │   ├── apis/v1/
│   │   │   ├── __init__.py                 # 라우터 등록
│   │   │   ├── auth_routers.py             # 카카오 OAuth 엔드포인트
│   │   │   ├── chat_routers.py             # 채팅 엔드포인트
│   │   │   └── user_routers.py             # 유저 프로필 엔드포인트
│   │   ├── core/
│   │   │   ├── config.py                   # 환경변수 설정
│   │   │   ├── db/postgres_client.py       # PostgreSQL 커넥션 풀 (psycopg3)
│   │   │   ├── jwt/                        # JWT 토큰 클래스
│   │   │   └── validators/                 # 유효성 검사
│   │   ├── dependencies/
│   │   │   └── security.py                 # Bearer 토큰 의존성
│   │   ├── dtos/
│   │   │   └── users.py                    # 응답 DTO
│   │   ├── models/
│   │   │   └── users.py                    # User Pydantic 모델
│   │   ├── repositories/
│   │   │   ├── user_repository.py          # PostgreSQL users CRUD
│   │   │   └── chat_repository.py          # PostgreSQL conversations/messages CRUD (+ PGvector)
│   │   ├── services/
│   │   │   ├── auth.py                     # Kakao OAuth 서비스
│   │   │   ├── chat.py                     # GPT-4o-mini + E-O 루프
│   │   │   ├── jwt.py                      # JWT 발급/검증 서비스
│   │   │   └── users.py                    # 유저 관리 서비스
│   │   ├── tests/                          # 테스트 코드
│   │   └── main.py                         # FastAPI 앱 진입점
│   ├── envs/example.local.env
│   ├── docker-compose.yml
│   ├── pyproject.toml
│   ├── PROJECT_DOCS.md                     # PDCA/E-O/Pipeline/Deploy 문서
│   └── FULL_IMPLEMENTATION.md              # 이 파일
│
└── frontend/                               # Next.js 프론트엔드
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx                        # 로그인 페이지
    │   ├── auth/kakao/callback/page.tsx    # OAuth 콜백
    │   └── chat/page.tsx                   # 채팅 메인
    ├── components/
    │   ├── ChatMessage.tsx
    │   ├── ChatInput.tsx
    │   └── ConversationSidebar.tsx
    └── lib/
        └── api.ts                          # axios 클라이언트
```

---

## 2. 데이터베이스 스키마 (PostgreSQL + PGvector + PostGIS)

PostgreSQL에 접속한 후 순서대로 실행하세요.  
Docker Compose 사용 시 `docker/postgres/init.sql`에 ①~② 를 넣으면 컨테이너 최초 기동 시 자동 실행됩니다.

```sql
-- ① 확장 설치 (최초 1회)
CREATE EXTENSION IF NOT EXISTS vector;    -- PGvector: 벡터 유사도 검색
CREATE EXTENSION IF NOT EXISTS postgis;   -- PostGIS: 지리공간 쿼리

-- ② users 테이블 (PostGIS location 컬럼 추가)
CREATE TABLE users (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  kakao_id        VARCHAR     UNIQUE NOT NULL,
  email           VARCHAR,
  nickname        VARCHAR     NOT NULL,
  profile_image   VARCHAR,
  location        GEOGRAPHY(POINT, 4326),  -- 사용자 위치 (경도, 위도)
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ③ conversations 테이블
CREATE TABLE conversations (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        REFERENCES users(id) ON DELETE CASCADE,
  title       VARCHAR     DEFAULT '새 대화',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ④ messages 테이블 (PGvector embedding 컬럼 추가)
CREATE TABLE messages (
  id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id     UUID        REFERENCES conversations(id) ON DELETE CASCADE,
  role                VARCHAR     NOT NULL CHECK (role IN ('user', 'assistant')),
  content             TEXT        NOT NULL,
  embedding           vector(1536),   -- OpenAI text-embedding-3-small 벡터
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ⑤ hospitals 테이블 (PostGIS 기반 병원 위치 정보)
CREATE TABLE hospitals (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        VARCHAR     NOT NULL,
  address     VARCHAR,
  phone       VARCHAR,
  specialty   VARCHAR,
  location    GEOGRAPHY(POINT, 4326) NOT NULL,  -- 병원 위치 (경도, 위도)
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ⑥ 인덱스 (조회 성능)
CREATE INDEX idx_conversations_user_id    ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);

-- PGvector IVFFlat 인덱스 (코사인 유사도 검색 — 데이터 1000건 이상 시 효과적)
CREATE INDEX idx_messages_embedding
  ON messages USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- PostGIS 공간 인덱스 (반경 검색 성능)
CREATE INDEX idx_hospitals_location ON hospitals USING GIST (location);
CREATE INDEX idx_users_location     ON users     USING GIST (location);
```

### PostGIS 활용 예시: 주변 병원 조회

```sql
-- 사용자 위치(위도 37.5665, 경도 126.9780) 기준 반경 5km 이내 병원 조회
SELECT
  name,
  address,
  phone,
  specialty,
  ST_Distance(location, ST_MakePoint(126.9780, 37.5665)::geography) AS distance_m
FROM hospitals
WHERE ST_DWithin(
  location,
  ST_MakePoint(126.9780, 37.5665)::geography,
  5000  -- 5000m = 5km
)
ORDER BY distance_m;
```

### PGvector 활용 예시: 유사 메시지 검색

```sql
-- 특정 임베딩 벡터와 코사인 유사도가 가장 높은 메시지 5개 조회
SELECT id, content, role, (embedding <=> '[0.01, 0.02, ...]'::vector) AS distance
FROM messages
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.01, 0.02, ...]'::vector
LIMIT 5;
```

---

## 3. 백엔드 전체 구현 코드

### 3-1. `pyproject.toml`

```toml
[project]
name = "ai-health-example"
version = "0.1.0"
description = "AI 헬스케어 파이널 프로젝트 예시용"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "cryptography>=46.0.3",
    "pydantic>=2.12.5",
    "pydantic-settings>=2.12.0",
    "python-dateutil>=2.9.0.post0",
    "redis>=7.1.0",
    "tomlkit>=0.14.0",
]

[dependency-groups]
app = [
    "bcrypt<=4.0.1",
    "fastapi[standard]>=0.128.0",
    "httpx>=0.28.1",
    "openai>=1.0.0",
    "orjson>=3.11.5",
    "passlib[bcrypt]>=1.7.4",
    "pgvector>=0.3.0",
    "psycopg[binary,pool]>=3.2.0",
    "pyjwt>=2.10.1",
    "uvicorn>=0.40.0",
]
dev = [
    "coverage>=7.13.2",
    "mypy>=1.19.1",
    "pytest-asyncio>=1.3.0",
    "pytest>=8.0.0",
    "ruff>=0.14.14",
    "types-passlib>=1.7.7.20250602",
    "types-python-dateutil>=2.9.0.20260124",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "C90", "B", "UP", "N"]
ignore = ["UP046", "E501"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

### 3-2. `envs/example.local.env`

```env
# Docker
DOCKER_USER=your-docker-username
DOCKER_REPOSITORY=medifind-bot
APP_VERSION=v1.0.0

# FastAPI
SECRET_KEY=your-very-strong-secret-key-change-in-production
COOKIE_DOMAIN=localhost
ENV=local

# PostgreSQL (PGvector + PostGIS)
DATABASE_URL=postgresql://medifind:medifind_password@localhost:5432/medifind

# OpenAI
OPENAI_API_KEY=sk-proj-...

# Kakao OAuth
KAKAO_CLIENT_ID=your-kakao-rest-api-key
KAKAO_CLIENT_SECRET=your-kakao-client-secret
KAKAO_REDIRECT_URI=http://localhost:3000/auth/kakao/callback

# Frontend CORS
FRONTEND_URL=http://localhost:3000
```

### 3-3. `app/core/config.py`

```python
import os
import uuid
import zoneinfo
from dataclasses import field
from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    ENV: Env = Env.LOCAL
    SECRET_KEY: str = f"default-secret-key{uuid.uuid4().hex}"
    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))
    TEMPLATE_DIR: str = os.path.join(Path(__file__).resolve().parent.parent, "templates")

    COOKIE_DOMAIN: str = "localhost"

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5

    # PostgreSQL (PGvector + PostGIS)
    DATABASE_URL: str = "postgresql://medifind:medifind_password@localhost:5432/medifind"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Kakao OAuth
    KAKAO_CLIENT_ID: str = ""
    KAKAO_CLIENT_SECRET: str = ""
    KAKAO_REDIRECT_URI: str = "http://localhost:3000/auth/kakao/callback"

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"


config = Config()
```

### 3-4. `app/core/db/postgres_client.py`

```python
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core import config

_pool: ConnectionPool | None = None


def init_db() -> None:
    """FastAPI lifespan에서 호출. 애플리케이션 시작 시 커넥션 풀을 초기화합니다."""
    global _pool
    _pool = ConnectionPool(
        conninfo=config.DATABASE_URL,
        min_size=2,
        max_size=10,
        kwargs={"row_factory": dict_row},
    )


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("DB pool이 초기화되지 않았습니다. init_db()를 먼저 호출하세요.")
    return _pool
```

### 3-5. `app/models/users.py`

```python
from datetime import datetime

from pydantic import BaseModel


class User(BaseModel):
    id: str
    kakao_id: str
    email: str | None = None
    nickname: str
    profile_image: str | None = None
    created_at: datetime | None = None
```

### 3-6. `app/repositories/user_repository.py`

```python
from app.core.db.postgres_client import get_pool
from app.models.users import User


class UserRepository:
    def get_user(self, user_id: str) -> User | None:
        with get_pool().connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = %s",
                (user_id,),
            ).fetchone()
        return User(**row) if row else None

    def get_by_kakao_id(self, kakao_id: str) -> User | None:
        with get_pool().connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE kakao_id = %s",
                (kakao_id,),
            ).fetchone()
        return User(**row) if row else None

    def upsert_kakao_user(
        self,
        kakao_id: str,
        nickname: str,
        email: str | None,
        profile_image: str | None,
    ) -> User:
        with get_pool().connection() as conn:
            row = conn.execute(
                """
                INSERT INTO users (kakao_id, nickname, email, profile_image)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (kakao_id)
                DO UPDATE SET
                    nickname      = EXCLUDED.nickname,
                    email         = EXCLUDED.email,
                    profile_image = EXCLUDED.profile_image
                RETURNING *
                """,
                (kakao_id, nickname, email, profile_image),
            ).fetchone()
        return User(**row)
```

### 3-7. `app/repositories/chat_repository.py`

```python
from pgvector.psycopg import register_vector

from app.core.db.postgres_client import get_pool


class ChatRepository:
    def create_conversation(self, user_id: str, title: str = "새 대화") -> dict:
        with get_pool().connection() as conn:
            return conn.execute(
                "INSERT INTO conversations (user_id, title) VALUES (%s, %s) RETURNING *",
                (user_id, title),
            ).fetchone()

    def get_conversations(self, user_id: str) -> list[dict]:
        with get_pool().connection() as conn:
            return conn.execute(
                "SELECT * FROM conversations WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()

    def get_conversation(self, conversation_id: str, user_id: str) -> dict | None:
        with get_pool().connection() as conn:
            return conn.execute(
                "SELECT * FROM conversations WHERE id = %s AND user_id = %s",
                (conversation_id, user_id),
            ).fetchone()

    def get_messages(self, conversation_id: str) -> list[dict]:
        with get_pool().connection() as conn:
            return conn.execute(
                "SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
                (conversation_id,),
            ).fetchall()

    def create_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        embedding: list[float] | None = None,
    ) -> dict:
        with get_pool().connection() as conn:
            register_vector(conn)
            return conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, embedding)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (conversation_id, role, content, embedding),
            ).fetchone()

    def search_similar_messages(self, embedding: list[float], limit: int = 5) -> list[dict]:
        """PGvector 코사인 유사도 기반 유사 메시지 검색 (RAG 활용 가능)"""
        with get_pool().connection() as conn:
            register_vector(conn)
            return conn.execute(
                """
                SELECT *, (embedding <=> %s) AS distance
                FROM messages
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (embedding, embedding, limit),
            ).fetchall()

    def delete_conversation(self, conversation_id: str, user_id: str) -> None:
        with get_pool().connection() as conn:
            conn.execute(
                "DELETE FROM conversations WHERE id = %s AND user_id = %s",
                (conversation_id, user_id),
            )
```

### 3-8. `app/services/auth.py`

```python
import httpx
from fastapi import HTTPException
from starlette import status

from app.core import config
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService
from app.core.jwt.tokens import AccessToken, RefreshToken

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_URL = "https://kapi.kakao.com/v2/user/me"


class AuthService:
    def __init__(self) -> None:
        self.user_repo = UserRepository()
        self.jwt_service = JwtService()

    def get_kakao_auth_url(self) -> str:
        return (
            f"https://kauth.kakao.com/oauth/authorize"
            f"?client_id={config.KAKAO_CLIENT_ID}"
            f"&redirect_uri={config.KAKAO_REDIRECT_URI}"
            f"&response_type=code"
        )

    async def exchange_kakao_code(self, code: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                KAKAO_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": config.KAKAO_CLIENT_ID,
                    "client_secret": config.KAKAO_CLIENT_SECRET,
                    "redirect_uri": config.KAKAO_REDIRECT_URI,
                    "code": code,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 토큰 발급 실패")
        return resp.json()["access_token"]

    async def get_kakao_user_info(self, kakao_access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                KAKAO_USER_URL,
                headers={"Authorization": f"Bearer {kakao_access_token}"},
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 사용자 정보 조회 실패")
        return resp.json()

    async def kakao_login(self, code: str) -> dict[str, AccessToken | RefreshToken]:
        kakao_token = await self.exchange_kakao_code(code)
        kakao_info = await self.get_kakao_user_info(kakao_token)

        kakao_id = str(kakao_info["id"])
        kakao_account = kakao_info.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        nickname = profile.get("nickname", "사용자")
        email = kakao_account.get("email")
        profile_image = profile.get("profile_image_url")

        user = self.user_repo.upsert_kakao_user(
            kakao_id=kakao_id,
            nickname=nickname,
            email=email,
            profile_image=profile_image,
        )
        return self.jwt_service.issue_jwt_pair(user)
```

### 3-9. `app/services/chat.py` (E-O 루프 포함 — 섹션 4 상세 설명)

> E-O 루프 전체 코드는 **섹션 4**에 상세히 기술됩니다.  
> 아래는 현재 구현 기준 코드이며, 섹션 4의 E-O 버전으로 교체하세요.

```python
from fastapi import HTTPException
from openai import OpenAI
from starlette import status

from app.core import config
from app.repositories.chat_repository import ChatRepository

SYSTEM_PROMPT = (
    "당신은 의료 정보 안내 챗봇입니다. "
    "증상, 약품, 병원 관련 정보를 친절하게 안내합니다. "
    "의료적 진단은 제공하지 않으며, 심각한 증상이 있을 경우 반드시 전문의 상담을 권고합니다. "
    "답변은 한국어로 제공합니다."
)

_openai = OpenAI(api_key=config.OPENAI_API_KEY)


class ChatService:
    def __init__(self) -> None:
        self.repo = ChatRepository()

    def create_conversation(self, user_id: str, title: str = "새 대화") -> dict:
        return self.repo.create_conversation(user_id=user_id, title=title)

    def get_conversations(self, user_id: str) -> list[dict]:
        return self.repo.get_conversations(user_id=user_id)

    def get_conversation_with_messages(self, conversation_id: str, user_id: str) -> dict:
        conv = self.repo.get_conversation(conversation_id=conversation_id, user_id=user_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대화를 찾을 수 없습니다.")
        messages = self.repo.get_messages(conversation_id=conversation_id)
        return {**conv, "messages": messages}

    def delete_conversation(self, conversation_id: str, user_id: str) -> None:
        conv = self.repo.get_conversation(conversation_id=conversation_id, user_id=user_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대화를 찾을 수 없습니다.")
        self.repo.delete_conversation(conversation_id=conversation_id, user_id=user_id)

    def send_message(self, conversation_id: str, user_id: str, content: str) -> dict:
        conv = self.repo.get_conversation(conversation_id=conversation_id, user_id=user_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대화를 찾을 수 없습니다.")

        self.repo.create_message(conversation_id=conversation_id, role="user", content=content)

        history = self.repo.get_messages(conversation_id=conversation_id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += [{"role": m["role"], "content": m["content"]} for m in history[-10:]]

        completion = _openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        assistant_content = completion.choices[0].message.content or ""

        assistant_msg = self.repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
        )
        return assistant_msg
```

### 3-10. `app/services/users.py`

```python
from app.models.users import User
from app.repositories.user_repository import UserRepository


class UserManageService:
    def __init__(self) -> None:
        self.repo = UserRepository()

    def get_user(self, user_id: str) -> User | None:
        return self.repo.get_user(user_id)
```

### 3-11. `app/services/jwt.py`

```python
from typing import Any, Literal, overload

from fastapi import HTTPException

from app.core.jwt.exceptions import ExpiredTokenError, TokenError
from app.core.jwt.tokens import AccessToken, RefreshToken


class JwtService:
    access_token_class = AccessToken
    refresh_token_class = RefreshToken

    def create_access_token(self, user: Any) -> AccessToken:
        return self.access_token_class.for_user(user)

    def create_refresh_token(self, user: Any) -> RefreshToken:
        return self.refresh_token_class.for_user(user)

    @overload
    def verify_jwt(self, token: str, token_type: Literal["access"]) -> AccessToken: ...

    @overload
    def verify_jwt(self, token: str, token_type: Literal["refresh"]) -> RefreshToken: ...

    def verify_jwt(self, token: str, token_type: Literal["access", "refresh"]) -> AccessToken | RefreshToken:
        token_class: type[AccessToken | RefreshToken]
        if token_type == "access":
            token_class = self.access_token_class
        else:
            token_class = self.refresh_token_class

        try:
            return token_class(token=token)
        except ExpiredTokenError as err:
            raise HTTPException(status_code=401, detail=f"{token_type} token has expired.") from err
        except TokenError as err:
            raise HTTPException(status_code=400, detail="Provided invalid token.") from err

    def refresh_jwt(self, refresh_token: str) -> AccessToken:
        verified_rt = self.verify_jwt(token=refresh_token, token_type="refresh")
        return verified_rt.access_token

    def issue_jwt_pair(self, user: Any) -> dict[str, AccessToken | RefreshToken]:
        rt = self.create_refresh_token(user)
        at = rt.access_token
        return {"access_token": at, "refresh_token": rt}
```

### 3-12. `app/apis/v1/auth_routers.py`

```python
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import JSONResponse as Response

from app.core import config
from app.core.config import Env
from app.services.auth import AuthService
from app.services.jwt import JwtService

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.get("/kakao/login", status_code=status.HTTP_200_OK)
async def kakao_login_url(
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    url = auth_service.get_kakao_auth_url()
    return Response(content={"auth_url": url}, status_code=status.HTTP_200_OK)


@auth_router.post("/kakao/callback", status_code=status.HTTP_200_OK)
async def kakao_callback(
    code: str,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    tokens = await auth_service.kakao_login(code)
    resp = Response(
        content={"access_token": str(tokens["access_token"])},
        status_code=status.HTTP_200_OK,
    )
    resp.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        httponly=True,
        secure=config.ENV == Env.PROD,
        domain=config.COOKIE_DOMAIN or None,
        expires=tokens["refresh_token"].payload["exp"],
        samesite="lax",
    )
    return resp


@auth_router.get("/token/refresh", status_code=status.HTTP_200_OK)
async def token_refresh(
    jwt_service: Annotated[JwtService, Depends(JwtService)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token이 없습니다.")
    access_token = jwt_service.refresh_jwt(refresh_token)
    return Response(
        content={"access_token": str(access_token)},
        status_code=status.HTTP_200_OK,
    )
```

### 3-13. `app/apis/v1/chat_routers.py`

```python
from typing import Annotated

from fastapi import APIRouter, Body, Depends, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.models.users import User
from app.services.chat import ChatService

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
    title: str = Body(default="새 대화", embed=True),
) -> Response:
    conv = chat_service.create_conversation(user_id=user.id, title=title)
    return Response(conv, status_code=status.HTTP_201_CREATED)


@chat_router.get("/conversations", status_code=status.HTTP_200_OK)
async def get_conversations(
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
) -> Response:
    convs = chat_service.get_conversations(user_id=user.id)
    return Response(convs, status_code=status.HTTP_200_OK)


@chat_router.get("/conversations/{conversation_id}", status_code=status.HTTP_200_OK)
async def get_conversation(
    conversation_id: str,
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
) -> Response:
    conv = chat_service.get_conversation_with_messages(conversation_id=conversation_id, user_id=user.id)
    return Response(conv, status_code=status.HTTP_200_OK)


@chat_router.post("/conversations/{conversation_id}/messages", status_code=status.HTTP_200_OK)
async def send_message(
    conversation_id: str,
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
    content: str = Body(..., embed=True),
) -> Response:
    msg = chat_service.send_message(conversation_id=conversation_id, user_id=user.id, content=content)
    return Response(msg, status_code=status.HTTP_200_OK)


@chat_router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    user: Annotated[User, Depends(get_request_user)],
    chat_service: Annotated[ChatService, Depends(ChatService)],
) -> None:
    chat_service.delete_conversation(conversation_id=conversation_id, user_id=user.id)
```

### 3-14. `app/apis/v1/user_routers.py`

```python
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.users import UserInfoResponse
from app.models.users import User

user_router = APIRouter(prefix="/users", tags=["users"])


@user_router.get("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def user_me_info(
    user: Annotated[User, Depends(get_request_user)],
) -> Response:
    return Response(UserInfoResponse.model_validate(user).model_dump(), status_code=status.HTTP_200_OK)
```

### 3-15. `app/dependencies/security.py`

```python
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService

security = HTTPBearer()


async def get_request_user(credential: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> User:
    token = credential.credentials
    verified = JwtService().verify_jwt(token=token, token_type="access")
    user_id = verified.payload["user_id"]
    user = UserRepository().get_user(user_id)
    if not user:
        raise HTTPException(detail="인증에 실패했습니다.", status_code=status.HTTP_401_UNAUTHORIZED)
    return user
```

### 3-16. `app/main.py`

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.apis.v1 import v1_routers
from app.core import config
from app.core.db.postgres_client import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()   # 애플리케이션 시작 시 PostgreSQL 커넥션 풀 초기화
    yield


app = FastAPI(
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_routers)
```

### 3-17. `docker-compose.yml`

```yaml
services:
  # 1. PostgreSQL (PGvector + PostGIS)
  postgres:
    build:
      context: .
      dockerfile: docker/postgres/Dockerfile
    container_name: postgres
    environment:
      POSTGRES_USER: medifind
      POSTGRES_PASSWORD: medifind_password
      POSTGRES_DB: medifind
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - ws
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U medifind -d medifind"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  # 2. Redis (JWT refresh token 캐싱)
  redis:
    image: redis:alpine
    container_name: redis
    networks:
      - ws
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 5s

  # 3. API Server (FastAPI)
  fastapi:
    container_name: fastapi
    build:
      context: .
      dockerfile: app/Dockerfile
      platforms:
        - linux/amd64
        - linux/arm64
    image: ${DOCKER_USER}/${DOCKER_REPOSITORY}:app-${APP_VERSION}
    env_file: .env
    command: |
      sh -c "uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    volumes:
      - ./app:/app/app
    restart: always
    ports:
      - "8000:8000"
    networks:
      - ws
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy

networks:
  ws:
    driver: bridge

volumes:
  postgres_data:
```

### 3-18. `docker/postgres/Dockerfile` (신규)

```dockerfile
FROM postgis/postgis:17-3.5
RUN apt-get update \
    && apt-get install -y postgresql-17-pgvector \
    && rm -rf /var/lib/apt/lists/*
```

### 3-19. `docker/postgres/init.sql` (신규)

```sql
-- 컨테이너 최초 기동 시 자동 실행: 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
```

---

## 4. E-O 자가최적화 루프 (핵심 구현)

### 개념

GPT-4o-mini 응답이 의료 AI 챗봇 기준에 부합하지 않을 경우  
**프롬프트를 자동 강화하여 최대 3회 재시도**하고, 기준 미달 시 안전 폴백 응답을 반환하는 루프.

```
입력 → 안전성 검사 → E-O 루프(최대 3회) → 품질 평가 → PASS/FAIL
                                                           ↓FAIL×3
                                                     SAFE_FALLBACK
```

### 상수 정의

```python
# 즉시 응급 안내로 전환하는 키워드
DANGER_KEYWORDS = [
    "자살", "자해", "독약", "극약", "과다복용",
    "수면제 다량", "농약 먹으면", "죽고 싶어", "목숨 끊"
]

# AI가 의료적 진단/처방을 주장하는 표현 (품질 실패 트리거)
MEDICAL_OVERREACH = [
    "진단해드리겠습니다", "처방해드리겠습니다",
    "치료해드릴게요", "이 약을 드세요", "확실히 이 병입니다"
]

MAX_RETRY = 3
MIN_RESPONSE_LENGTH = 20

EMERGENCY_RESPONSE = (
    "⚠️ 응급 상황이 의심됩니다. "
    "즉시 119에 전화하거나 가까운 응급실을 방문해 주세요. "
    "전문 의료진의 도움을 받으시기 바랍니다."
)

SAFE_FALLBACK = (
    "죄송합니다. 현재 적절한 의료 정보를 제공하기 어렵습니다. "
    "증상이 심각하거나 지속된다면 반드시 전문의를 방문하시거나 "
    "응급 상황 시 119에 연락하세요."
)
```

### QualityChecker 클래스

```python
class QualityChecker:
    @staticmethod
    def is_safe_input(content: str) -> bool:
        """입력에 위험 키워드가 없으면 True"""
        return not any(kw in content for kw in DANGER_KEYWORDS)

    @staticmethod
    def is_quality_ok(text: str) -> bool:
        """응답이 품질 기준을 통과하면 True"""
        if len(text.strip()) < MIN_RESPONSE_LENGTH:
            return False
        if any(kw in text for kw in MEDICAL_OVERREACH):
            return False
        return True

    @staticmethod
    def build_prompt(history: list[dict], content: str, attempt: int) -> list[dict]:
        """재시도 횟수에 따라 시스템 프롬프트를 점진적으로 강화"""
        base = SYSTEM_PROMPT
        if attempt == 1:
            base += (
                " 절대로 진단, 처방, 치료를 직접 제공하지 마세요. "
                "반드시 '전문의 상담을 권고합니다'로 마무리하세요."
            )
        elif attempt >= 2:
            base += (
                " 진단이나 처방 없이, 일반적인 의료 정보만 안내하세요. "
                "구체적인 약 이름이나 치료법을 직접 지시하지 마세요. "
                "모든 답변 마지막에 전문의 상담을 권고하세요."
            )
        messages = [{"role": "system", "content": base}]
        messages += [{"role": m["role"], "content": m["content"]} for m in history[-10:]]
        return messages
```

### E-O 루프 적용 `send_message` (전체 교체 코드)

`app/services/chat.py`를 아래 코드로 교체하세요:

```python
from fastapi import HTTPException
from openai import OpenAI
from starlette import status

from app.core import config
from app.repositories.chat_repository import ChatRepository

SYSTEM_PROMPT = (
    "당신은 의료 정보 안내 챗봇입니다. "
    "증상, 약품, 병원 관련 정보를 친절하게 안내합니다. "
    "의료적 진단은 제공하지 않으며, 심각한 증상이 있을 경우 반드시 전문의 상담을 권고합니다. "
    "답변은 한국어로 제공합니다."
)

DANGER_KEYWORDS = [
    "자살", "자해", "독약", "극약", "과다복용",
    "수면제 다량", "농약 먹으면", "죽고 싶어", "목숨 끊",
]

MEDICAL_OVERREACH = [
    "진단해드리겠습니다", "처방해드리겠습니다",
    "치료해드릴게요", "이 약을 드세요", "확실히 이 병입니다",
]

MAX_RETRY = 3
MIN_RESPONSE_LENGTH = 20

EMERGENCY_RESPONSE = (
    "⚠️ 응급 상황이 의심됩니다. "
    "즉시 119에 전화하거나 가까운 응급실을 방문해 주세요. "
    "전문 의료진의 도움을 받으시기 바랍니다."
)

SAFE_FALLBACK = (
    "죄송합니다. 현재 적절한 의료 정보를 제공하기 어렵습니다. "
    "증상이 심각하거나 지속된다면 반드시 전문의를 방문하시거나 "
    "응급 상황 시 119에 연락하세요."
)

_openai = OpenAI(api_key=config.OPENAI_API_KEY)


def _is_safe_input(content: str) -> bool:
    return not any(kw in content for kw in DANGER_KEYWORDS)


def _is_quality_ok(text: str) -> bool:
    if len(text.strip()) < MIN_RESPONSE_LENGTH:
        return False
    if any(kw in text for kw in MEDICAL_OVERREACH):
        return False
    return True


def _build_messages(history: list[dict], attempt: int) -> list[dict]:
    base = SYSTEM_PROMPT
    if attempt == 1:
        base += (
            " 절대로 진단, 처방, 치료를 직접 제공하지 마세요. "
            "반드시 '전문의 상담을 권고합니다'로 마무리하세요."
        )
    elif attempt >= 2:
        base += (
            " 진단이나 처방 없이 일반적인 의료 정보만 안내하세요. "
            "구체적인 약 이름이나 치료법을 직접 지시하지 마세요. "
            "모든 답변 마지막에 전문의 상담을 권고하세요."
        )
    messages = [{"role": "system", "content": base}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history[-10:]]
    return messages


class ChatService:
    def __init__(self) -> None:
        self.repo = ChatRepository()

    def create_conversation(self, user_id: str, title: str = "새 대화") -> dict:
        return self.repo.create_conversation(user_id=user_id, title=title)

    def get_conversations(self, user_id: str) -> list[dict]:
        return self.repo.get_conversations(user_id=user_id)

    def get_conversation_with_messages(self, conversation_id: str, user_id: str) -> dict:
        conv = self.repo.get_conversation(conversation_id=conversation_id, user_id=user_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대화를 찾을 수 없습니다.")
        messages = self.repo.get_messages(conversation_id=conversation_id)
        return {**conv, "messages": messages}

    def delete_conversation(self, conversation_id: str, user_id: str) -> None:
        conv = self.repo.get_conversation(conversation_id=conversation_id, user_id=user_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대화를 찾을 수 없습니다.")
        self.repo.delete_conversation(conversation_id=conversation_id, user_id=user_id)

    def send_message(self, conversation_id: str, user_id: str, content: str) -> dict:
        conv = self.repo.get_conversation(conversation_id=conversation_id, user_id=user_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대화를 찾을 수 없습니다.")

        # [1] 위험 키워드 입력 안전성 검사
        if not _is_safe_input(content):
            assistant_msg = self.repo.create_message(
                conversation_id=conversation_id,
                role="assistant",
                content=EMERGENCY_RESPONSE,
            )
            return assistant_msg

        # [2] 사용자 메시지 저장
        self.repo.create_message(conversation_id=conversation_id, role="user", content=content)

        # [3] 히스토리 조회
        history = self.repo.get_messages(conversation_id=conversation_id)

        # [4] E-O 자가최적화 루프 (최대 MAX_RETRY회 재시도)
        assistant_content = SAFE_FALLBACK
        for attempt in range(MAX_RETRY):
            messages = _build_messages(history, attempt)
            completion = _openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            text = completion.choices[0].message.content or ""

            if _is_quality_ok(text):
                assistant_content = text
                break

        # [5] 최종 응답 저장 및 반환
        assistant_msg = self.repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
        )
        return assistant_msg
```

### E-O 루프 동작 시나리오

| 시나리오 | 입력 | 결과 |
|----------|------|------|
| 정상 의료 질문 | "두통이 자주 있어요" | GPT 응답 (attempt 0 PASS) |
| 위험 키워드 | "약을 많이 먹고 싶어" | EMERGENCY_RESPONSE 즉시 반환 |
| 너무 짧은 응답 | GPT → "네." | attempt 1 재시도 |
| 월권 표현 포함 | GPT → "진단해드리겠습니다" | attempt 1 (강화 프롬프트) 재시도 |
| 3회 모두 실패 | — | SAFE_FALLBACK 반환 |

---

## 5. 프론트엔드 전체 구현 코드

### 5-1. `package.json`

```json
{
  "name": "frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "axios": "^1.16.1",
    "next": "16.2.6",
    "react": "19.2.4",
    "react-dom": "19.2.4"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4",
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "eslint": "^9",
    "eslint-config-next": "16.2.6",
    "tailwindcss": "^4",
    "typescript": "^5"
  }
}
```

### 5-2. `.env.local` 템플릿

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_KAKAO_CLIENT_ID=your-kakao-rest-api-key
```

### 5-3. `lib/api.ts`

```typescript
import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  withCredentials: true,
});

// 요청 인터셉터: localStorage에서 JWT 자동 첨부
api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 응답 인터셉터: 401 시 토큰 자동 갱신
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        const res = await axios.get(`${BASE_URL}/api/v1/auth/token/refresh`, {
          withCredentials: true,
        });
        localStorage.setItem("access_token", res.data.access_token);
        error.config.headers.Authorization = `Bearer ${res.data.access_token}`;
        return api(error.config);
      } catch {
        localStorage.removeItem("access_token");
        window.location.href = "/";
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  getKakaoLoginUrl: () => api.get<{ auth_url: string }>("/auth/kakao/login"),
  kakaoCallback: (code: string) =>
    api.post<{ access_token: string }>("/auth/kakao/callback", null, { params: { code } }),
};

export const userApi = {
  getMe: () => api.get("/users/me"),
};

export const chatApi = {
  createConversation: (title?: string) =>
    api.post("/chat/conversations", { title: title || "새 대화" }),
  getConversations: () => api.get("/chat/conversations"),
  getConversation: (id: string) => api.get(`/chat/conversations/${id}`),
  sendMessage: (conversationId: string, content: string) =>
    api.post(`/chat/conversations/${conversationId}/messages`, { content }),
  deleteConversation: (id: string) => api.delete(`/chat/conversations/${id}`),
};
```

### 5-4. `app/layout.tsx`

```typescript
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MediFind Bot",
  description: "의료 정보 AI 챗봇",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
```

### 5-5. `app/page.tsx`

```typescript
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) router.replace("/chat");
  }, [router]);

  const handleKakaoLogin = () => {
    const clientId = process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID;
    const redirectUri = `${window.location.origin}/auth/kakao/callback`;
    window.location.href =
      `https://kauth.kakao.com/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code`;
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl shadow-lg p-10 flex flex-col items-center gap-6 w-80">
        <h1 className="text-2xl font-bold text-gray-800">MediFind Bot</h1>
        <p className="text-sm text-gray-500 text-center">
          의료 정보 AI 챗봇에 오신 것을 환영합니다.
        </p>
        <button
          onClick={handleKakaoLogin}
          className="w-full bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold py-3 px-4 rounded-xl flex items-center justify-center gap-2 transition"
        >
          <span className="text-lg">💬</span>
          카카오로 로그인
        </button>
      </div>
    </main>
  );
}
```

### 5-6. `app/auth/kakao/callback/page.tsx`

```typescript
"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api";

function KakaoCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      router.replace("/");
      return;
    }

    authApi
      .kakaoCallback(code)
      .then((res) => {
        localStorage.setItem("access_token", res.data.access_token);
        router.replace("/chat");
      })
      .catch(() => {
        router.replace("/");
      });
  }, [router, searchParams]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <p className="text-gray-500">로그인 처리 중...</p>
    </main>
  );
}

export default function KakaoCallbackPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen flex items-center justify-center bg-gray-50">
          <p className="text-gray-500">로그인 처리 중...</p>
        </main>
      }
    >
      <KakaoCallbackInner />
    </Suspense>
  );
}
```

### 5-7. `app/chat/page.tsx`

```typescript
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { chatApi } from "@/lib/api";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import ConversationSidebar from "@/components/ConversationSidebar";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

interface Conversation {
  id: string;
  title: string;
  created_at: string;
}

export default function ChatPage() {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/");
      return;
    }
    loadConversations();
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadConversations = async () => {
    try {
      const res = await chatApi.getConversations();
      setConversations(res.data);
    } catch {
      router.replace("/");
    }
  };

  const selectConversation = async (id: string) => {
    setActiveId(id);
    const res = await chatApi.getConversation(id);
    setMessages(res.data.messages || []);
  };

  const createConversation = async () => {
    const res = await chatApi.createConversation();
    const newConv: Conversation = res.data;
    setConversations((prev) => [newConv, ...prev]);
    setActiveId(newConv.id);
    setMessages([]);
  };

  const deleteConversation = async (id: string) => {
    await chatApi.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) {
      setActiveId(null);
      setMessages([]);
    }
  };

  const sendMessage = async (content: string) => {
    if (!activeId) {
      const res = await chatApi.createConversation(content.slice(0, 30));
      const newConv: Conversation = res.data;
      setConversations((prev) => [newConv, ...prev]);
      setActiveId(newConv.id);
      await doSend(newConv.id, content);
    } else {
      await doSend(activeId, content);
    }
  };

  const doSend = async (convId: string, content: string) => {
    const userMsg: Message = {
      id: `temp-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);
    try {
      const res = await chatApi.sendMessage(convId, content);
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== userMsg.id),
        { ...userMsg, id: `user-${Date.now()}` },
        res.data as Message,
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.replace("/");
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConversation}
        onNew={createConversation}
        onDelete={deleteConversation}
        onLogout={handleLogout}
      />

      <main className="flex flex-col flex-1 overflow-hidden">
        {activeId ? (
          <>
            <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
              {messages.length === 0 && (
                <p className="text-center text-gray-400 text-sm mt-10">
                  궁금한 의료 정보를 질문해보세요.
                </p>
              )}
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {sending && (
                <div className="flex justify-start mb-3">
                  <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-2 text-sm text-gray-400">
                    답변 작성 중...
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <ChatInput onSend={sendMessage} disabled={sending} />
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
            <p className="text-lg mb-4">새 대화를 시작하거나</p>
            <p className="text-lg mb-6">기존 대화를 선택하세요.</p>
            <button
              onClick={createConversation}
              className="px-6 py-3 bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold rounded-xl transition"
            >
              새 대화 시작
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
```

### 5-8. `components/ChatMessage.tsx`

```typescript
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export default function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs mr-2 shrink-0 mt-1">
          AI
        </div>
      )}
      <div
        className={`max-w-[70%] px-4 py-2 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-yellow-400 text-gray-900 rounded-br-sm"
            : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
```

### 5-9. `components/ChatInput.tsx`

```typescript
"use client";

import { useState, KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-end gap-2 border-t border-gray-200 p-4 bg-white">
      <textarea
        className="flex-1 resize-none rounded-xl border border-gray-300 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 max-h-32"
        rows={1}
        placeholder="메시지를 입력하세요... (Shift+Enter 줄바꿈)"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        className="px-4 py-3 bg-yellow-400 hover:bg-yellow-500 disabled:bg-gray-200 disabled:text-gray-400 text-gray-900 font-semibold rounded-xl text-sm transition"
      >
        전송
      </button>
    </div>
  );
}
```

### 5-10. `components/ConversationSidebar.tsx`

```typescript
"use client";

interface Conversation {
  id: string;
  title: string;
  created_at: string;
}

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onLogout: () => void;
}

export default function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onLogout,
}: Props) {
  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col h-full">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-lg font-bold">MediFind Bot</h1>
        <p className="text-xs text-gray-400 mt-0.5">의료 정보 AI 챗봇</p>
      </div>

      <div className="p-3">
        <button
          onClick={onNew}
          className="w-full text-left px-3 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm transition"
        >
          + 새 대화
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 space-y-1">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`group flex items-center rounded-lg px-3 py-2 cursor-pointer text-sm transition ${
              activeId === conv.id ? "bg-gray-600" : "hover:bg-gray-700"
            }`}
            onClick={() => onSelect(conv.id)}
          >
            <span className="flex-1 truncate">{conv.title}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(conv.id);
              }}
              className="hidden group-hover:block text-gray-400 hover:text-red-400 ml-1 text-xs"
            >
              ✕
            </button>
          </div>
        ))}
      </nav>

      <div className="p-3 border-t border-gray-700">
        <button
          onClick={onLogout}
          className="w-full text-left px-3 py-2 text-sm text-gray-400 hover:text-white transition"
        >
          로그아웃
        </button>
      </div>
    </aside>
  );
}
```

---

## 6. CI/CD 및 테스트 코드

### 6-1. `.github/workflows/checks.yml` (개선 버전)

> 변경사항: `feature/*` 브랜치 트리거 추가, Supabase 제거 → PostgreSQL(PGvector) CI 서비스 추가

```yaml
name: ci.yml

on:
  push:
    branches:
      - main
      - develop
      - 'feature/*'
      - 'release/*'
      - 'hotfix/*'
  pull_request:
    branches:
      - main
      - develop
      - 'release/*'
      - 'hotfix/*'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: uv sync --frozen

      - name: Run Ruff Check (Linting)
        run: uv run ruff check .

      - name: Run Ruff Format Check
        run: uv run ruff format . --check

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg17
        env:
          POSTGRES_USER: medifind
          POSTGRES_PASSWORD: medifind_password
          POSTGRES_DB: medifind
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql://medifind:medifind_password@localhost:5432/medifind
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      KAKAO_CLIENT_ID: ${{ secrets.KAKAO_CLIENT_ID }}
      KAKAO_CLIENT_SECRET: ${{ secrets.KAKAO_CLIENT_SECRET }}
      SECRET_KEY: ${{ secrets.SECRET_KEY }}
      ENV: dev
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: uv sync --group app --group dev --frozen

      - name: Apply DB schema
        run: |
          PGPASSWORD=medifind_password psql -h localhost -U medifind -d medifind \
            -c "CREATE EXTENSION IF NOT EXISTS vector;" \
            -c "CREATE EXTENSION IF NOT EXISTS postgis;" \
            -f docker/postgres/init.sql || true

      - name: Check if tests exist
        id: check_tests
        run: |
          if [ -d "app/tests" ] || [ $(find . -name "test_*.py" | wc -l) -gt 0 ]; then
            echo "has_tests=true" >> $GITHUB_OUTPUT
          else
            echo "has_tests=false" >> $GITHUB_OUTPUT
          fi

      - name: Run Tests with Coverage
        if: steps.check_tests.outputs.has_tests == 'true'
        run: |
          uv run coverage run -m pytest app/tests -v
          uv run coverage report -m
```

> **GitHub Repository Secrets 등록 필요:**
> `Settings → Secrets and variables → Actions → New repository secret`
> - `DATABASE_URL` (선택 — CI는 하드코딩, 운영 환경은 Secret 사용 권장)
> - `OPENAI_API_KEY`
> - `KAKAO_CLIENT_ID`
> - `KAKAO_CLIENT_SECRET`
> - `SECRET_KEY`

### 6-2. `app/tests/conftest.py` (PostgreSQL mock 기반)

```python
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_db():
    """psycopg3 ConnectionPool mock — get_pool().connection() 컨텍스트 매니저 모사"""
    with patch("app.core.db.postgres_client._pool") as mock_pool:
        mock_conn = MagicMock()
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_conn


@pytest.fixture
def mock_openai():
    with patch("app.services.chat._openai") as mock:
        choice = MagicMock()
        choice.message.content = "두통은 긴장성 두통일 수 있습니다. 충분한 휴식을 취하시고 증상이 지속되면 전문의 상담을 권고합니다."
        mock.chat.completions.create.return_value = MagicMock(choices=[choice])
        yield mock


@pytest.fixture
def sample_user():
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "kakao_id": "123456789",
        "email": "test@example.com",
        "nickname": "테스트유저",
        "profile_image": None,
        "location": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.fixture
def auth_headers(sample_user):
    from app.services.jwt import JwtService
    from app.models.users import User

    user = User(**sample_user)
    tokens = JwtService().issue_jwt_pair(user)
    return {"Authorization": f"Bearer {str(tokens['access_token'])}"}
```

### 6-3. `app/tests/auth_apis/test_kakao_callback.py`

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestKakaoCallback:
    def test_kakao_login_url(self, client):
        """카카오 로그인 URL 반환 테스트"""
        response = client.get("/api/v1/auth/kakao/login")
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "kauth.kakao.com/oauth/authorize" in data["auth_url"]

    def test_kakao_callback_success(self, client, mock_db, sample_user):
        """카카오 콜백 성공 — JWT 발급 테스트"""
        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {"access_token": "kakao_token_abc"}

        mock_user_resp = MagicMock()
        mock_user_resp.status_code = 200
        mock_user_resp.json.return_value = {
            "id": 123456789,
            "kakao_account": {
                "email": "test@kakao.com",
                "profile": {
                    "nickname": "테스트유저",
                    "profile_image_url": None,
                },
            },
        }

        # upsert_kakao_user → fetchone() 반환값 설정
        mock_db.execute.return_value.fetchone.return_value = sample_user

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_token_resp):
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_user_resp):
                response = client.post("/api/v1/auth/kakao/callback", params={"code": "test_code"})

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_kakao_callback_invalid_code(self, client):
        """잘못된 code → 400 반환 테스트"""
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"error": "invalid_grant"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            response = client.post("/api/v1/auth/kakao/callback", params={"code": "bad_code"})

        assert response.status_code == 400
```

### 6-4. `app/tests/chat_apis/test_chat_api.py`

```python
import pytest
from unittest.mock import MagicMock, call

CONV_ID = "conv-uuid-1234"
USER_ID = "550e8400-e29b-41d4-a716-446655440000"
SAMPLE_CONV = {
    "id": CONV_ID,
    "user_id": USER_ID,
    "title": "새 대화",
    "created_at": "2026-01-01T00:00:00+00:00",
}
SAMPLE_MSG = {
    "id": "msg-uuid-1",
    "conversation_id": CONV_ID,
    "role": "assistant",
    "content": "두통은 긴장성 두통일 수 있습니다. 전문의 상담을 권고합니다.",
    "embedding": None,
    "created_at": "2026-01-01T00:00:01+00:00",
}
SAMPLE_USER = {
    "id": USER_ID,
    "kakao_id": "123456789",
    "nickname": "테스트",
    "email": None,
    "profile_image": None,
    "location": None,
    "created_at": "2026-01-01T00:00:00+00:00",
}


class TestChatConversations:
    def test_create_conversation(self, client, mock_db, auth_headers):
        """새 대화 생성 테스트"""
        # get_request_user → get_user
        mock_db.execute.return_value.fetchone.side_effect = [SAMPLE_USER, SAMPLE_CONV]

        response = client.post("/api/v1/chat/conversations", json={"title": "새 대화"}, headers=auth_headers)
        assert response.status_code == 201

    def test_send_message_normal(self, client, mock_db, mock_openai, auth_headers):
        """정상 메시지 전송 + E-O 루프 PASS 테스트"""
        mock_db.execute.return_value.fetchone.side_effect = [SAMPLE_USER, SAMPLE_CONV, SAMPLE_MSG]
        mock_db.execute.return_value.fetchall.return_value = []

        response = client.post(
            f"/api/v1/chat/conversations/{CONV_ID}/messages",
            json={"content": "두통이 자주 있어요"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_send_message_danger_keyword(self, client, mock_db, auth_headers):
        """위험 키워드 입력 시 EMERGENCY_RESPONSE 반환 테스트"""
        emergency_msg = {**SAMPLE_MSG, "content": "⚠️ 응급 상황이 의심됩니다."}
        mock_db.execute.return_value.fetchone.side_effect = [SAMPLE_USER, SAMPLE_CONV, emergency_msg]

        response = client.post(
            f"/api/v1/chat/conversations/{CONV_ID}/messages",
            json={"content": "자살하고 싶어요"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "응급" in response.json().get("content", "")

    def test_get_conversation_not_found(self, client, mock_db, auth_headers):
        """존재하지 않는 대화 조회 → 404 테스트"""
        # get_user 성공, get_conversation → None 반환
        mock_db.execute.return_value.fetchone.side_effect = [SAMPLE_USER, None]

        response = client.get("/api/v1/chat/conversations/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404
```

---

## 로컬 실행 빠른 참조

```bash
# ── 백엔드 (AI_HealthCare_Final_Project_Template/) ──

# 1. 환경변수 설정
cp envs/example.local.env .env
# .env 파일에서 OPENAI_API_KEY, KAKAO_* 값 입력

# 2. PostgreSQL (PGvector + PostGIS) + Redis 기동
docker compose up postgres redis -d

# 3. DB 스키마 적용 (최초 1회 — init.sql이 자동 실행되지 않은 경우)
docker exec -i postgres psql -U medifind -d medifind < docker/postgres/init.sql

# 4. 의존성 설치 및 서버 실행
uv sync --group app
uv run uvicorn app.main:app --reload --port 8000

# ── 프론트엔드 (frontend/) ──
cp .env.local.example .env.local  # KAKAO_CLIENT_ID 입력
npm install
npm run dev   # http://localhost:3000

# ── Swagger UI ──
# http://localhost:8000/api/docs

# ── DB 접속 확인 ──
docker exec -it postgres psql -U medifind -d medifind
# \dx   → vector, postgis 확장 설치 확인
# \dt   → 테이블 목록 확인
```

---

*이 문서는 `feature/chatbot` 브랜치 기준 전체 구현 코드를 포함합니다.*  
*데이터베이스: PostgreSQL 17 + PGvector(벡터 유사도 검색) + PostGIS(지리공간 쿼리) Self-hosted*  
*E-O 루프 적용은 섹션 4의 전체 교체 코드를 `app/services/chat.py`에 반영하세요.*
