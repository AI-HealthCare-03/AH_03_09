# AI 헬스케어 플랫폼 — 개발 가이드라인

> 대상: 백엔드 서버(`app/`) + AI 워커(`ai_worker/`) 구현 담당자  
> 기준 코드: 베이스라인 커밋 기준 / 요구사항 정의서 최종본 반영

---

## 목차

1. [전체 아키텍처](#1-전체-아키텍처)
2. [디렉터리 구조](#2-디렉터리-구조)
3. [백엔드 레이어 규칙](#3-백엔드-레이어-규칙)
4. [AI 워커 구현 가이드](#4-ai-워커-구현-가이드)
5. [신규 도메인 추가 절차](#5-신규-도메인-추가-절차)
6. [보안 구현 가이드](#6-보안-구현-가이드)
7. [마이그레이션 관리](#7-마이그레이션-관리)
8. [테스트 작성 규칙](#8-테스트-작성-규칙)
9. [인프라 및 실행 환경](#9-인프라-및-실행-환경)
10. [미구현 기능 구현 순서](#10-미구현-기능-구현-순서)

---

## 1. 전체 아키텍처

```
클라이언트
    │
    ▼
[Nginx :80]
    │  reverse proxy
    ▼
[FastAPI :8000]  ──── MySQL :3306
    │  lpush(task)         (Tortoise ORM + Aerich)
    ▼
[Redis :6379]
    │  blpop(task)
    ▼
[AI Worker]  ──── (LLM / OCR / RAG 모델)
    │  lpush(result)
    ▼
[Redis]
    │  blpop(result, timeout=30s)
    ▼
[FastAPI]  ──── 응답 반환
```

### 서비스별 역할

| 서비스 | 컨테이너 | 역할 |
|--------|----------|------|
| `fastapi` | `app/` | HTTP API, 인증, 비즈니스 로직, DB I/O |
| `ai-worker` | `ai_worker/` | LLM 추론, OCR 처리, RAG 파이프라인 |
| `mysql` | - | 영구 데이터 저장 |
| `redis` | - | FastAPI ↔ AI Worker 비동기 작업 큐 |
| `nginx` | `infra/nginx/` | 정적파일, 리버스 프록시, TLS 종단 |

### 핵심 통신 패턴 — Redis 큐

```
FastAPI (Producer)
  └─ redis.lpush("ai:chat:queue", payload_json)

AI Worker (Consumer)
  └─ redis.blpop("ai:chat:queue", timeout=0)   # 무한 대기
  └─ 처리 완료 후 redis.lpush("ai:chat:result:{task_id}", result_json)
  └─ redis.expire(result_key, 300)             # 5분 TTL

FastAPI (Result Poller)
  └─ redis.blpop("ai:chat:result:{task_id}", timeout=30)  # 30초 타임아웃
```

큐 이름과 결과 키 접두사는 양쪽(`app/services/chats.py`, `ai_worker/main.py`)에서 **상수로 일치**시켜야 한다.

---

## 2. 디렉터리 구조

```
project-root/
├── app/                         # FastAPI 백엔드 서버
│   ├── main.py                  # FastAPI 앱 초기화 + Tortoise 등록
│   ├── apis/v1/                 # HTTP 라우터 (엔드포인트)
│   ├── services/                # 비즈니스 로직 레이어
│   ├── repositories/            # DB 쿼리 레이어
│   ├── models/                  # Tortoise ORM 모델
│   ├── dtos/                    # Pydantic 요청/응답 스키마
│   ├── dependencies/            # FastAPI Depends 팩토리
│   ├── core/
│   │   ├── config.py            # 환경변수 설정 (Pydantic Settings)
│   │   ├── db/databases.py      # Tortoise 설정 + 모델 등록
│   │   ├── db/migrations/       # Aerich 마이그레이션 파일
│   │   ├── jwt/                 # JWT 토큰 발급/검증
│   │   ├── utils/               # 공통 유틸 (security, phone 등)
│   │   └── validators/          # Pydantic AfterValidator 함수들
│   └── tests/                   # pytest 테스트
│
├── ai_worker/                   # AI 추론 워커 (독립 프로세스)
│   ├── main.py                  # Redis 큐 소비 루프
│   ├── core/config.py           # 워커 전용 설정
│   ├── schemas/                 # 큐 페이로드 Pydantic 스키마
│   └── tasks/                   # 실제 AI 처리 함수
│
├── infra/nginx/                 # Nginx 설정
├── docs/                        # 문서
├── docker-compose.yml
└── pyproject.toml               # uv 의존성 관리
```

---

## 3. 백엔드 레이어 규칙

코드는 아래 단방향 의존 흐름을 반드시 따른다.

```
Router → Service → Repository → Model
  DTO ──────────────────────────────▶
```

### 3-1. Model (`app/models/`)

- 모든 모델은 `tortoise.models.Model`을 상속
- PK는 `BigIntField(primary_key=True)` 고정
- FK는 `ForeignKeyField("models.ModelName", on_delete=fields.CASCADE)`
- `created_at = DatetimeField(auto_now_add=True)` / `updated_at = DatetimeField(auto_now=True)` 기본 포함
- 불변 이력 테이블(예: `HealthProfileHistory`)은 `updated_at` 생략
- Enum 컬럼은 `CharEnumField(enum_type=MyEnum)` — `max_length` 불필요

```python
# 패턴 예시
class ExerciseHabit(StrEnum):
    REGULAR = "REGULAR"
    NONE = "NONE"

class HealthProfile(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE, unique=True)
    lifestyle_exercise = fields.CharEnumField(enum_type=ExerciseHabit, default=ExerciseHabit.NONE)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "health_profiles"
```

새 모델 파일 생성 후 반드시 `app/core/db/databases.py`의 `TORTOISE_APP_MODELS`에 추가한다.

---

### 3-2. Repository (`app/repositories/`)

- DB 쿼리만 담당. 비즈니스 로직 **금지**
- `self._model = MyModel` 패턴으로 모델 참조
- 반환 타입은 항상 `Model | None` 또는 `list[Model]`로 명시

```python
class HealthProfileRepository:
    def __init__(self):
        self._model = HealthProfile

    async def get_by_user_id(self, user_id: int) -> HealthProfile | None:
        return await self._model.get_or_none(user_id=user_id)

    async def create(self, user_id: int, **kwargs) -> HealthProfile:
        return await self._model.create(user_id=user_id, **kwargs)

    async def update_instance(self, profile: HealthProfile, data: dict) -> None:
        for key, value in data.items():
            setattr(profile, key, value)
        await profile.save(update_fields=list(data.keys()) + ["updated_at"])
```

---

### 3-3. Service (`app/services/`)

- 비즈니스 로직 + 트랜잭션 관리
- DB 변경이 필요한 모든 쓰기 작업은 `async with in_transaction():` 사용
- HTTP 예외는 서비스에서 `raise HTTPException(...)` — 라우터에서 처리하지 않음

```python
from tortoise.transactions import in_transaction

class HealthProfileService:
    def __init__(self):
        self.repo = HealthProfileRepository()

    async def get_or_create_profile(self, user: User) -> HealthProfile:
        profile = await self.repo.get_by_user_id(user.id)
        if not profile:
            async with in_transaction():
                profile = await self.repo.create(user_id=user.id)
        return profile

    async def update_profile(self, user: User, data: HealthProfileUpdateRequest) -> HealthProfile:
        profile = await self.repo.get_by_user_id(user.id)
        if not profile:
            raise HTTPException(status_code=404, detail="건강 프로필이 존재하지 않습니다.")
        async with in_transaction():
            # 변경 이력 저장
            await HealthProfileHistoryRepository().create_snapshot(
                health_profile_id=profile.id,
                snapshot=...,   # profile 현재 상태를 dict로 직렬화
                changed_by=ProfileChangedBy.USER,
            )
            await self.repo.update_instance(profile, data.model_dump(exclude_none=True))
            await profile.refresh_from_db()
        return profile
```

---

### 3-4. DTO (`app/dtos/`)

- 요청 스키마: `pydantic.BaseModel` 상속
- 응답 스키마(ORM 직렬화): `BaseSerializerModel` 상속 (`model_config = ConfigDict(from_attributes=True)` 포함)
- 선택적 업데이트 필드는 `field: Type | None = None`
- 유효성 검사는 `AfterValidator`로 분리 (`app/core/validators/`)

```python
# 요청
class HealthProfileUpdateRequest(BaseModel):
    primary_conditions: list[str] | None = None
    lifestyle_exercise: ExerciseHabit | None = None
    lifestyle_smoking: bool | None = None

# 응답
class HealthProfileResponse(BaseSerializerModel):
    id: int
    primary_conditions: list
    lifestyle_exercise: ExerciseHabit
    lifestyle_smoking: bool
    updated_at: datetime
```

---

### 3-5. Router (`app/apis/v1/`)

- 엔드포인트 함수는 얇게 유지 — 인증/의존성 주입 + 서비스 호출 + 응답 반환만
- 인증이 필요한 라우터: `user: Annotated[User, Depends(get_request_user)]`
- 응답은 `ORJSONResponse(content.model_dump(), status_code=...)` 패턴

```python
health_router = APIRouter(prefix="/health-profile", tags=["health-profile"])

@health_router.get("", response_model=HealthProfileResponse)
async def get_health_profile(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HealthProfileService, Depends(HealthProfileService)],
) -> Response:
    result = await service.get_or_create_profile(user)
    return Response(HealthProfileResponse.model_validate(result).model_dump())

@health_router.patch("", response_model=HealthProfileResponse)
async def update_health_profile(
    body: HealthProfileUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HealthProfileService, Depends(HealthProfileService)],
) -> Response:
    result = await service.update_profile(user, body)
    return Response(HealthProfileResponse.model_validate(result).model_dump())
```

새 라우터는 `app/apis/v1/__init__.py`에 반드시 등록한다.

```python
# app/apis/v1/__init__.py
from app.apis.v1.health_profile_routers import health_router

v1_routers.include_router(health_router)
```

---

## 4. AI 워커 구현 가이드

### 4-1. 워커 실행 흐름

```python
# ai_worker/main.py (현행 구조 유지)
async def run_worker(redis):
    while True:
        raw = await redis.blpop(AI_TASK_QUEUE, timeout=0)
        payload = ChatTaskPayload.model_validate_json(raw[1])
        result = await generate_chat_response(payload)          # ← 여기 구현
        await redis.lpush(f"{AI_RESULT_PREFIX}{result.task_id}", result.model_dump_json())
        await redis.expire(result_key, AI_RESULT_TTL)
```

### 4-2. LLM 연동 (`ai_worker/tasks/chat_task.py`)

현재 `generate_chat_response`는 플레이스홀더. 아래 절차로 실제 모델로 교체한다.

**Step 1 — 모델 초기화 (워커 기동 시 1회)**

```python
# ai_worker/tasks/chat_task.py
from sentence_transformers import SentenceTransformer
# 또는 transformers, openai SDK 등 선택

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("snunlp/KR-SBERT-V40K-klueNLI-augSTS")  # 예시
    return _model
```

**Step 2 — 채팅 이력 로드 (RAG 컨텍스트 구성)**

AI 워커도 MySQL에 직접 접근해야 한다면 `ai_worker/core/config.py`에 DB 설정을 추가하고 Tortoise를 독립 초기화한다. 단순 RAG 구성이라면 FastAPI에서 이력을 Redis 페이로드에 포함시켜 워커에 전달하는 방식이 더 간단하다.

```python
# app/services/chats.py — 페이로드에 이력 포함
history = await self.message_repo.get_messages_by_session(session_id=session.id)
payload = json.dumps({
    "task_id": task_id,
    "session_id": session_id,
    "user_message": data.content,
    "history": [{"role": m.role, "content": m.content} for m in history],
})
```

```python
# ai_worker/schemas/chats.py — 스키마 확장
class HistoryItem(BaseModel):
    role: str
    content: str

class ChatTaskPayload(BaseModel):
    task_id: str
    session_id: int
    user_message: str
    history: list[HistoryItem] = []
```

**Step 3 — 실제 LLM 호출**

```python
async def generate_chat_response(payload: ChatTaskPayload) -> ChatTaskResult:
    model = get_model()
    # 이력 + 현재 질문을 프롬프트로 구성
    context = "\n".join(f"[{h.role}] {h.content}" for h in payload.history[-10:])
    prompt = f"{context}\n[USER] {payload.user_message}\n[ASSISTANT]"

    # 모델 추론 (동기 함수는 asyncio.to_thread로 감쌀 것)
    answer = await asyncio.to_thread(_run_inference, model, prompt)
    return ChatTaskResult(task_id=payload.task_id, answer=answer)

def _run_inference(model, prompt: str) -> str:
    # 실제 모델 추론 로직
    ...
```

**주의:** CPU-bound 추론 함수는 반드시 `asyncio.to_thread()`로 실행해 이벤트 루프를 블록하지 않는다.

### 4-3. OCR 처리 태스크 추가

OCR은 채팅과 별도 큐를 사용한다. 큐 이름을 상수로 관리한다.

```python
# ai_worker/main.py — 복수 큐 처리
QUEUES = [AI_TASK_QUEUE, OCR_TASK_QUEUE]

raw = await redis.blpop(QUEUES, timeout=0)
queue_name, payload_json = raw

if queue_name == AI_TASK_QUEUE:
    ...
elif queue_name == OCR_TASK_QUEUE:
    payload = OcrTaskPayload.model_validate_json(payload_json)
    result = await process_ocr(payload)
    ...
```

```python
# ai_worker/tasks/ocr_task.py
async def process_ocr(payload: OcrTaskPayload) -> OcrTaskResult:
    # 1. 파일 경로에서 이미지 로드
    # 2. 전처리 (grayscale, denoise)
    # 3. OCR 엔진 호출 (pytesseract, EasyOCR, 또는 외부 API)
    # 4. 결과 구조화 (structured_data JSON)
    # 5. PII 마스킹
    ...
```

### 4-4. 의존성 그룹 사용법

```bash
# AI 워커 전용 의존성 설치
uv sync --group ai

# 앱 서버 전용 의존성 설치
uv sync --group app

# 전체 개발환경
uv sync --all-groups
```

---

## 5. 신규 도메인 추가 절차

예: **건강 프로필(HealthProfile)** 도메인을 추가하는 경우

```
① 모델 확인/생성       app/models/health_profiles.py          (완료)
② 마이그레이션 생성     aerich migrate --name add_health_models  (완료)
③ Repository 생성      app/repositories/health_profile_repository.py
④ DTO 생성             app/dtos/health_profiles.py
⑤ Service 생성         app/services/health_profiles.py
⑥ Router 생성          app/apis/v1/health_profile_routers.py
⑦ Router 등록          app/apis/v1/__init__.py
⑧ 테스트 작성          app/tests/health_profile_apis/
```

**체크리스트**

- [ ] 모델이 `TORTOISE_APP_MODELS`에 등록되어 있는가?
- [ ] 마이그레이션이 `aerich upgrade`로 적용되었는가?
- [ ] 인증이 필요한 엔드포인트에 `get_request_user` Depends가 있는가?
- [ ] 소유권 검증이 서비스 레이어에 있는가? (다른 사용자 데이터 접근 차단)
- [ ] 쓰기 작업에 `in_transaction()`이 적용되었는가?
- [ ] 응답 DTO가 `BaseSerializerModel`을 상속하는가?

---

## 6. 보안 구현 가이드

### 6-1. JWT 인증 흐름

```
로그인 → AccessToken(60분) + RefreshToken(14일) 발급
         └─ AccessToken: Authorization Bearer 헤더
         └─ RefreshToken: httpOnly Secure 쿠키

토큰 만료 → GET /api/v1/auth/token/refresh (쿠키의 refresh_token 사용)
           → 새 AccessToken 반환
```

`get_request_user` 의존성(`app/dependencies/security.py`)이 Bearer 토큰을 검증하고 `User` 객체를 반환한다. 모든 인증 필요 엔드포인트에서 이 의존성을 사용한다.

### 6-2. 비밀번호 해싱

`app/core/utils/security.py`의 `hash_password()` / `verify_password()` 사용. bcrypt 알고리즘 고정. 직접 bcrypt를 호출하지 않는다.

### 6-3. 의료 데이터 암호화 (AES-256)

`OCRResult.extracted_text` 등 민감 의료 정보는 DB 저장 전 암호화, 조회 후 복호화한다.

```python
# app/core/utils/encryption.py (신규 작성 필요)
from cryptography.fernet import Fernet
from app.core import config

_fernet = Fernet(config.ENCRYPTION_KEY)  # .env에 ENCRYPTION_KEY 추가

def encrypt(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()

def decrypt(cipher: str) -> str:
    return _fernet.decrypt(cipher.encode()).decode()
```

서비스 레이어에서 저장 시 `encrypt()`, 읽기 시 `decrypt()`를 호출한다. Repository는 암호화 여부를 알지 못한다.

### 6-4. 소유권 검증 (필수)

모든 리소스 조회/수정/삭제에서 요청 사용자가 해당 리소스의 소유자인지 서비스 레이어에서 반드시 검증한다.

```python
# 잘못된 패턴 (user_id 필터 없음)
session = await self.session_repo.get_by_id(session_id)

# 올바른 패턴
session = await self.session_repo.get_by_id_and_user(session_id, user_id=user.id)
if not session:
    raise HTTPException(status_code=404, detail="리소스를 찾을 수 없습니다.")
```

### 6-5. 환경변수 (.env)

| 변수 | 설명 | 비고 |
|------|------|------|
| `SECRET_KEY` | JWT 서명 키 | 프로덕션에서 강한 랜덤값 필수 |
| `ENCRYPTION_KEY` | AES-256 Fernet 키 | `Fernet.generate_key()` 생성 |
| `DB_PASSWORD` | MySQL 비밀번호 | - |
| `ENV` | `local` / `dev` / `prod` | 쿠키 Secure 여부 결정 |

---

## 7. 마이그레이션 관리

```bash
# 새 마이그레이션 생성 (모델 변경 후)
uv run aerich migrate --name <설명>

# DB 적용
uv run aerich upgrade

# 마이그레이션 현황 확인
uv run aerich history

# 롤백
uv run aerich downgrade -v <버전번호>
```

**규칙**

- 마이그레이션 파일은 직접 수정하지 않는다. 문제 있으면 `downgrade` 후 재생성.
- `downgrade()` SQL은 항상 작성한다 (`DROP TABLE IF EXISTS ...`).
- 팀원 간 마이그레이션 파일 번호가 충돌하면 더 높은 번호로 재생성 후 PR에서 합친다.

---

## 8. 테스트 작성 규칙

### 구조

```
app/tests/
├── conftest.py                  # DB 초기화, 인증 픽스처
├── auth_apis/
│   └── test_auth.py
├── user_apis/
│   └── test_users.py
└── chat_apis/
    └── test_chats.py
```

### pytest 설정

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
```

### 기본 픽스처 패턴

```python
# app/tests/conftest.py 참고 패턴
import pytest
from httpx import AsyncClient, ASGITransport
from tortoise import Tortoise

from app.main import app

@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.fixture
async def auth_headers(client):
    # 테스트 사용자 생성 + 로그인 → Authorization 헤더 반환
    ...
```

### 테스트 작성 원칙

- 외부 서비스(Redis, AI Worker)는 `unittest.mock.patch`로 모킹
- DB는 실제 테스트 DB 사용 (인메모리 SQLite는 JSON 컬럼 미지원으로 금지)
- 각 테스트는 독립적으로 실행 가능해야 함 (픽스처로 데이터 격리)

---

## 9. 인프라 및 실행 환경

### 로컬 개발

```bash
# 의존성 설치
uv sync --group app --group dev

# 인프라 (MySQL + Redis) 기동
docker compose up mysql redis -d

# 마이그레이션 적용
uv run aerich upgrade

# FastAPI 서버 기동
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# AI 워커 기동 (별도 터미널)
uv sync --group ai
uv run python -m ai_worker.main
```

### Docker Compose 전체 기동

```bash
cp .env.example .env   # 환경변수 설정
docker compose up --build
```

### 서비스 의존 관계

```
nginx → fastapi → mysql (healthy)
                → redis (healthy)
ai-worker       → mysql (healthy)
                → redis (healthy)
```

`healthcheck`가 설정되어 있으므로 MySQL/Redis가 준비되기 전에 앱이 뜨는 문제는 없다.

### 포트 정리

| 서비스 | 포트 | 비고 |
|--------|------|------|
| Nginx | 80 | 외부 진입점 |
| FastAPI | 8000 | 직접 개발 시 |
| MySQL | `DB_EXPOSE_PORT` (.env) | 로컬 접속용 |
| Redis | 6379 | - |

---

## 10. 미구현 기능 구현 순서

요구사항 정의서 기준 우선순위 순서.

### Phase 1 — 건강 프로필 (REQ-LLM)

**목표:** 온보딩 시 건강 정보 수집 및 수정 API

```
app/repositories/health_profile_repository.py
app/dtos/health_profiles.py
app/services/health_profiles.py
app/apis/v1/health_profile_routers.py
```

핵심 API:
- `GET  /api/v1/health-profile` — 조회 (없으면 기본값 생성)
- `PATCH /api/v1/health-profile` — 수정 (변경 시 History 자동 기록)
- `GET  /api/v1/health-profile/history` — 12개월 변경 이력 조회

---

### Phase 2 — 의료 문서 OCR (REQ-OCR)

**목표:** 문서 업로드 → AI 워커 OCR 처리 → 결과 확인

```
# 백엔드
app/repositories/medical_document_repository.py
app/dtos/medical_documents.py
app/services/medical_documents.py
app/apis/v1/document_routers.py

# AI 워커
ai_worker/schemas/ocr.py
ai_worker/tasks/ocr_task.py
```

핵심 API:
- `POST /api/v1/documents/upload` — 파일 업로드 (multipart/form-data, ≤ 10MB)
- `POST /api/v1/documents/{id}/ocr` — OCR 처리 요청 (Redis 큐 발행)
- `GET  /api/v1/documents/{id}` — 문서 + OCR 결과 조회
- `PATCH /api/v1/documents/{id}/verify` — 사용자 OCR 결과 확인

구현 시 주의:
- 파일은 S3 또는 로컬 스토리지에 저장 후 경로만 DB에 기록
- `extracted_text` 저장 전 AES-256 암호화 (`encrypt()` 호출)
- OCR 결과 조회 시 복호화 후 반환
- `confidence_score < 70`이면 `requires_manual_review = True` 플래그

---

### Phase 3 — 처방전/약물 정보 (REQ-LLM)

**목표:** OCR 결과에서 약물 정보 자동 추출 + 수동 입력

```
app/repositories/medication_repository.py
app/dtos/medications.py
app/services/medications.py
app/apis/v1/medication_routers.py
```

핵심 API:
- `GET  /api/v1/medications` — 내 약물 목록
- `POST /api/v1/medications` — 수동 입력
- `POST /api/v1/documents/{id}/extract-medications` — OCR 결과에서 자동 추출
- `PATCH /api/v1/medications/{id}` — 수정
- `DELETE /api/v1/medications/{id}` — 삭제

---

### Phase 4 — AI 챗봇 실제 LLM 연동 (REQ-CHAT)

**목표:** `ai_worker/tasks/chat_task.py` 플레이스홀더를 실제 모델로 교체

구현 항목:
1. `ai_worker/tasks/chat_task.py` — 실제 LLM 호출 로직
2. 채팅 이력 페이로드 포함 (FastAPI → Redis → Worker)
3. 건강 프로필/약물 정보를 시스템 프롬프트에 주입 (RAG)
4. 안전 가드레일: 응급 상황 감지 시 119 안내 문구 삽입
5. 신뢰도 낮은 응답에 "전문가 상담 권장" 면책 문구 자동 추가

---

### Phase 5 — 건강 안내 (REQ-LLM)

**목표:** LLM이 생성한 맞춤형 건강 안내 저장 및 관리

```
app/repositories/health_guidance_repository.py
app/dtos/health_guidances.py
app/services/health_guidances.py
app/apis/v1/guidance_routers.py
```

핵심 API:
- `POST /api/v1/guidances/medication` — 약물 안내 생성
- `POST /api/v1/guidances/lifestyle` — 생활습관 안내 생성
- `GET  /api/v1/guidances` — 내 안내 목록
- `PATCH /api/v1/guidances/{id}/verify` — 관리자/전문가 검증 처리

---

### 공통 구현 필요 항목

| 항목 | 위치 | 비고 |
|------|------|------|
| AES-256 암호화 유틸 | `app/core/utils/encryption.py` | `cryptography` 패키지 기사용 |
| 파일 업로드 유틸 | `app/core/utils/storage.py` | S3 or 로컬 |
| 30일 비활성 계정 처리 | 스케줄러 또는 로그인 시 검사 | `is_active = False` 처리 |
| 채팅 이력 6개월 보존 정책 | 배치 스케줄러 | APScheduler or Celery beat |
