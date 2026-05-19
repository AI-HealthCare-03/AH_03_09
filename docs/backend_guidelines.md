# 백엔드 개발 가이드라인

약봉투·처방전 OCR 기반 복약 관리 서비스 — FastAPI 백엔드 개발 기준 문서

---

## 1. 프로젝트 디렉토리 구조

```
AH_03_09/
├── app/                        # FastAPI 서버
│   ├── main.py                 # 앱 진입점 (lifespan, CORS, router 등록)
│   ├── apis/v1/                # API 라우터
│   │   ├── __init__.py         # v1_routers 집합 (prefix=/api/v1)
│   │   ├── auth_routers.py
│   │   ├── chat_routers.py
│   │   ├── user_routers.py
│   │   └── ocr/                # OCR 전용 서브폴더
│   │       ├── __init__.py
│   │       └── ocr_routers.py
│   ├── core/                   # 인프라/공통
│   │   ├── config.py           # Pydantic Settings (환경변수)
│   │   ├── logger.py
│   │   ├── redis_client.py
│   │   └── db/
│   │       ├── postgres_client.py  # psycopg3 ConnectionPool (users용)
│   │       ├── databases.py        # Tortoise ORM 설정 (chat용)
│   │       └── sqlalchemy_client.py # SQLAlchemy async engine (ocr용)
│   ├── dependencies/
│   │   └── security.py         # get_request_user (JWT HTTPBearer)
│   ├── models/                 # ORM/Pydantic 모델
│   │   ├── users.py            # Pydantic (psycopg3용 DTO)
│   │   ├── chat.py             # Tortoise ORM
│   │   └── ocr/                # OCR 전용 서브폴더
│   │       ├── __init__.py
│   │       ├── base.py         # SQLAlchemy DeclarativeBase
│   │       └── ocr_document.py # OCR SQLAlchemy 모델 4종
│   ├── dtos/                   # Pydantic 요청/응답 스키마
│   │   ├── base.py
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── users.py
│   │   └── ocr/                # OCR 전용 서브폴더
│   │       └── document_dtos.py
│   ├── repositories/           # DB 쿼리 레이어
│   │   ├── user_repository.py
│   │   ├── chat_repository.py
│   │   └── ocr/                # OCR 전용 서브폴더
│   │       └── document_repository.py
│   ├── services/               # 비즈니스 로직
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── jwt.py
│   │   ├── users.py
│   │   └── ocr/                # OCR 전용 서브폴더
│   │       └── document_service.py
│   └── tests/
│       ├── conftest.py
│       ├── auth_apis/
│       ├── chat_apis/
│       └── ocr_apis/           # OCR 전용 테스트 서브폴더
│
├── ai_worker/                  # AI 추론 워커 (OpenAI 스트리밍)
├── docker/postgres/init.sql    # DB 테이블 DDL (단일 진실 원천)
├── docker-compose.yml
├── pyproject.toml              # uv 의존성 관리
└── envs/                       # 환경변수 파일
    ├── example.local.env
    └── .local.env              # 실제 사용 (gitignore)
```

---

## 2. 핵심 아키텍처 패턴

### 요청 흐름

```
HTTP 요청
  └─ Router (app/apis/v1/)
       └─ Service (app/services/)
            └─ Repository (app/repositories/)
                 └─ DB (psycopg3 / Tortoise ORM / SQLAlchemy)
```

### 규칙
- Router는 HTTP 처리만. 비즈니스 로직은 Service로 위임
- Service는 DB를 직접 호출하지 않고 Repository를 통해서만 접근
- Repository는 단일 도메인의 쿼리만 담당
- 인증이 필요한 엔드포인트는 반드시 `Depends(get_request_user)` 사용

---

## 3. DB 접근 패턴 (3-Layer)

프로젝트는 도메인별로 다른 DB 접근 방식을 사용합니다.

### 3-1. psycopg3 raw SQL — `users` 도메인

```python
# app/repositories/user_repository.py
from app.core.db.postgres_client import get_pool

class UserRepository:
    def get_user(self, user_id: str) -> User | None:
        with get_pool().connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()
        return User(**row) if row else None
```

- `app/core/db/postgres_client.py`의 `get_pool()` 사용
- `init_db()`는 `app/main.py` lifespan에서 호출
- 반환값은 `app/models/users.py`의 Pydantic `User` 모델

### 3-2. Tortoise ORM — `chat` 도메인

```python
# app/repositories/chat_repository.py
from app.models.chat import ChatSession

class ChatRepository:
    async def create_session(self, user_id: str, title: str) -> ChatSession:
        return await ChatSession.create(user_id=user_id, title=title)
```

- `app/models/chat.py`의 Tortoise `models.Model` 서브클래스 사용
- 모든 메서드 `async def`
- `TORTOISE_APP_MODELS`에 모델 경로 등록 필요

### 3-3. SQLAlchemy async — `ocr` 도메인 (신규)

```python
# app/repositories/ocr/document_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ocr.ocr_document import OcrDocument

class OcrDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs) -> OcrDocument:
        doc = OcrDocument(**kwargs)
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc
```

- `app/core/db/sqlalchemy_client.py`의 `get_async_session()` dependency 주입
- 모든 메서드 `async def`
- `app/models/ocr/base.py`의 `Base` 공유

---

## 4. JWT 인증

### 플로우

```
클라이언트 → Kakao OAuth → /api/v1/auth/kakao/callback
  └─ JWT 발급: access_token (60분) + refresh_token (14일, httpOnly cookie)

보호 엔드포인트:
  Authorization: Bearer <access_token>
  └─ HTTPBearer → get_request_user() → User 객체 반환
```

### 사용법

```python
from typing import Annotated
from fastapi import Depends
from app.dependencies.security import get_request_user
from app.models.users import User

@router.get("/protected")
async def protected_endpoint(
    current_user: Annotated[User, Depends(get_request_user)],
):
    return {"user_id": current_user.id}
```

### 구현 파일
- `app/core/jwt/backends.py` — PyJWT encode/decode
- `app/core/jwt/tokens.py` — AccessToken / RefreshToken 클래스
- `app/services/jwt.py` — JwtService (issue, verify, refresh)
- `app/dependencies/security.py` — `get_request_user` FastAPI dependency

---

## 5. API 라우터 패턴

```python
# app/apis/v1/ocr/ocr_routers.py
from fastapi import APIRouter

ocr_router = APIRouter(prefix="/ocr", tags=["ocr"])

@ocr_router.get("/health")
async def health_check():
    return {"status": "ok"}
```

### 라우터 등록 (`app/apis/v1/__init__.py`)

```python
from fastapi import APIRouter
from app.apis.v1.ocr.ocr_routers import ocr_router

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(ocr_router)
# 결과: GET /api/v1/ocr/health
```

---

## 6. DTO (Pydantic) 패턴

```python
# app/dtos/base.py
from pydantic import BaseModel, ConfigDict

class BaseSerializerModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

```python
# app/dtos/ocr/document_dtos.py
from app.dtos.base import BaseSerializerModel

class OcrDocumentResponse(BaseSerializerModel):
    id: str
    status: str
    doc_type: str | None = None

# 라우터에서 사용
return OcrDocumentResponse.model_validate(orm_object)
```

**규칙:**
- DB ORM 객체 → DTO 변환은 `model_validate(obj)` 사용 (`from_attributes=True` 필요)
- `Optional[X]` 대신 `X | None` 사용 (Python 3.10+)
- 응답 모델은 `response_model=` 파라미터로 명시

---

## 7. 테스트 패턴

### conftest.py 공용 fixtures

| fixture | 설명 |
|---------|------|
| `client` | TestClient (init_db mock 포함) |
| `mock_db` | psycopg3 ConnectionPool mock |
| `sample_user` | 테스트용 User dict |
| `auth_headers` | Bearer JWT 헤더 |

### 작성 방법 (Service mock 패턴)

```python
# app/tests/ocr_apis/test_ocr_router.py
from unittest.mock import MagicMock, patch

class TestOcrHealth:
    def test_health_check(self, client):
        response = client.get("/api/v1/ocr/health")
        assert response.status_code == 200

class TestOcrDocuments:
    def test_list_documents(self, client, mock_db, auth_headers):
        mock_db.execute.return_value.fetchone.return_value = {...}  # sample_user

        with patch("app.apis.v1.ocr.ocr_routers.OcrDocumentService") as mock_svc:
            mock_svc.return_value.list_documents = AsyncMock(return_value=[])
            response = client.get("/api/v1/ocr/documents", headers=auth_headers)

        assert response.status_code == 200
```

**핵심 규칙:**
- 실제 DB(PostgreSQL)에 연결하지 않음 — 모든 DB 호출 mock
- `AsyncMock` 사용 대상: async 함수, async context manager
- `MagicMock` 사용 대상: 일반 sync 함수

---

## 8. CI/CD 규칙

### Ruff 설정 (pyproject.toml)

| 항목 | 설정 |
|------|------|
| 줄 길이 | 120자 |
| 따옴표 | 큰따옴표 `"` |
| import 순서 | isort 자동 정렬 (I rules) |
| `__init__.py` | F401(unused import) 무시 |

### 자주 발생하는 Ruff 오류

```python
# 잘못된 예
from typing import Optional
def foo(x: Optional[str]) -> None: ...  # UP007: use X | None

# 올바른 예
def foo(x: str | None) -> None: ...

# 잘못된 예 (미사용 import)
import os  # F401

# 잘못된 예 (UP006)
from typing import List, Dict
def foo() -> List[str]: ...

# 올바른 예
def foo() -> list[str]: ...
```

### CI 파이프라인

```yaml
# .github/workflows/checks.yml
lint: uv run ruff check . && uv run ruff format . --check
test: uv run coverage run -m pytest app && uv run coverage report -m
```

**CI 실패 방지 체크리스트:**
1. `uv run ruff check .` 로컬 실행 후 에러 0 확인
2. `uv run ruff format . --check` 포맷 확인
3. `uv run pytest app` 모든 테스트 통과
4. 새 파일 추가 시 `app/tests/`에 대응 테스트 작성

---

## 9. OCR 파트 개발 규칙

### 폴더 격리 원칙

OCR 관련 코드는 반드시 `ocr/` 서브폴더에 위치:

```
app/apis/v1/ocr/      # 라우터
app/models/ocr/       # SQLAlchemy 모델
app/dtos/ocr/         # Pydantic 스키마
app/repositories/ocr/ # DB 쿼리
app/services/ocr/     # 비즈니스 로직
app/tests/ocr_apis/   # 테스트
```

### OCR 도메인 테이블

| 테이블 | 역할 |
|--------|------|
| `ocr_documents` | 업로드 파일 메타데이터 (S3 키, 상태) |
| `ocr_results` | Clova OCR API 원본 결과 |
| `medications` | 파싱된 약물 정보 |
| `disease_codes` | ICD-10 질병분류기호 |

### SQLAlchemy 의존성 주입 패턴

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db.sqlalchemy_client import get_async_session

@ocr_router.get("/documents")
async def list_documents(
    current_user: Annotated[User, Depends(get_request_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    ...
```

---

## 10. Docker Compose 서비스

| 서비스 | 포트 | 역할 |
|--------|------|------|
| `redis` | 6379 | JWT 캐싱, Pub/Sub, Celery broker |
| `postgres` | 5432 | PostgreSQL 16 + pgvector |
| `fastapi` | 8000 | FastAPI 서버 (--reload) |
| `ai-worker` | - | OpenAI 스트리밍 워커 |
| `nginx` | 80 | 리버스 프록시 |

### 로컬 개발 실행

```bash
# 최초 세팅 (테이블 재생성)
docker-compose down -v
docker-compose up -d postgres redis

# 서버 실행
docker-compose up fastapi

# 로그 확인
docker-compose logs -f fastapi
```

### DB 초기화 확인

```bash
docker exec postgres psql -U $DB_USER -d $DB_NAME -c "\dt"
```

---

## 11. 환경변수 구성

`envs/example.local.env` 참고. 실제 개발 환경은 `envs/.local.env` (gitignore됨).

| 변수 | 설명 |
|------|------|
| `DATABASE_URL` | `postgresql://user:pw@host:5432/db` |
| `REDIS_URL` | `redis://localhost:6379` |
| `SECRET_KEY` | JWT 서명 키 |
| `KAKAO_CLIENT_ID/SECRET` | Kakao OAuth |
| `CLOVA_OCR_API_URL` | Clova OCR API endpoint |
| `CLOVA_OCR_SECRET_KEY` | Clova OCR 인증 키 |
| `AWS_ACCESS_KEY_ID` | S3 업로드용 |
| `AWS_SECRET_ACCESS_KEY` | S3 업로드용 |
| `AWS_S3_BUCKET_NAME` | 파일 저장 버킷명 |

---

## 12. 의존성 그룹

```toml
# pyproject.toml
[dependency-groups]
app = [...]    # FastAPI 서버 의존성
ai = [...]     # AI 워커 의존성 (torch 등)
dev = [...]    # 개발 도구 (ruff, pytest)
```

새 패키지 추가:
```bash
uv add <package> --group app   # 서버 의존성
uv add <package> --group dev   # 개발 도구
```

CI에서 설치:
```bash
uv sync --frozen --group app --no-group ai  # 서버 테스트
uv sync --frozen --only-group dev           # lint만
```
