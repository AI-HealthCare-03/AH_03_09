# System Design — AI Healthcare Platform

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                         │
│              React + Vite (localhost:3000)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼──────────────────────────────────┐
│                       Nginx (port 80)                        │
│              Reverse Proxy + Static File Serving             │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend (port 8000)                  │
│  Router → Service → Repository → Tortoise ORM               │
└───────────┬──────────────────────────────┬──────────────────┘
            │ lpush (task)                 │ blpop (result)
┌───────────▼──────────────┐   ┌───────────▼──────────────────┐
│      Redis Queue         │   │       MySQL Database          │
│   ai:chat:queue          │   │  users, chat_sessions,        │
│   ai:chat:stream:{id}    │   │  chat_messages,               │
│   ai:chat:result:{id}    │   │  health_profiles,             │
└───────────┬──────────────┘   │  medical_documents, ...       │
            │ blpop (task)     └──────────────────────────────┘
┌───────────▼──────────────────────────────────────────────────┐
│                      AI Worker (async)                        │
│   OpenAI GPT-4o-mini  │  OCR (future)  │  Embedding (future) │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. 채팅 비동기 처리 설계 결정

### 설계 후보 비교

| 항목 | Polling | **SSE Streaming (채택)** |
|------|---------|--------------------------|
| 흐름 | POST → `job_id` → GET /status 반복 | POST /stream → 청크 실시간 수신 |
| 서버 부하 | 폴링 요청 N회 발생 | 단일 연결 유지 |
| UX | 완료 후 전체 텍스트 한 번에 | 글자 단위 실시간 표시 |
| 구현 복잡도 | status 엔드포인트 별도 필요 | StreamingResponse 단일 처리 |
| 적합 상황 | 수 분 이상 소요되는 배치 작업 | 텍스트 생성 (수 초 이내) |

### 채택 이유

다이어그램의 "비동기 처리 → AI 워커 → 응답 조합" 흐름은 SSE로 완전히 구현됩니다.
- **Redis Queue**: FastAPI가 `lpush`로 즉시 반환 → AI Worker가 `blpop`으로 비동기 처리 ✓
- **실시간 응답**: 폴링 대신 SSE 청크 스트림으로 Polling보다 나은 UX ✓
- **DB 저장**: 스트림 완료(`DONE` sentinel) 시점에 전체 메시지 저장 ✓

---

## 4. Chat Flow (Non-Streaming)

```
User                  FastAPI              Redis             AI Worker           OpenAI
 │                       │                   │                   │                 │
 │── POST /messages ────▶│                   │                   │                 │
 │                       │── lpush(task) ───▶│                   │                 │
 │                       │                   │── blpop(task) ───▶│                 │
 │                       │                   │                   │── chat.create ─▶│
 │                       │                   │                   │◀─ answer ───────│
 │                       │                   │◀─ lpush(result) ──│                 │
 │                       │◀─ blpop(result) ──│                   │                 │
 │                       │  [save to DB]     │                   │                 │
 │◀── 200 ChatMessage ───│                   │                   │                 │
```

---

## 5. Chat Flow (SSE Streaming)

```
User                  FastAPI              Redis             AI Worker           OpenAI
 │                       │                   │                   │                 │
 │── POST /stream ──────▶│                   │                   │                 │
 │                       │── lpush(task,     │                   │                 │
 │                       │    stream=True) ──▶                   │                 │
 │◀── SSE open ──────────│                   │── blpop(task) ───▶│                 │
 │                       │                   │                   │── stream=True ─▶│
 │                       │                   │                   │◀─ chunk[0] ─────│
 │                       │                   │◀─ rpush(chunk) ───│                 │
 │◀── data: {chunk} ─────│◀─ blpop ──────────│                   │                 │
 │                       │                   │◀─ rpush(chunk) ───│   ...chunks...  │
 │◀── data: {chunk} ─────│◀─ blpop ──────────│                   │                 │
 │                       │                   │◀─ rpush(DONE) ────│                 │
 │                       │  [save to DB]     │                   │                 │
 │◀── event: done ───────│                   │                   │                 │
```

---

## 6. Health Profile → Chat Context Injection

```
send_message()
     │
     ├── get_messages_by_session()  → history[]
     │
     ├── get_by_user_id()           → health_profile{}
     │        │
     │        └── if exists → inject into Redis payload:
     │              {
     │                primary_conditions, allergies,
     │                current_medications, lifestyle_*
     │              }
     │
     └── AI Worker: _build_system_prompt()
              │
              ├── if health_profile is None → BASE_SYSTEM_PROMPT
              │
              └── if health_profile exists →
                    BASE_SYSTEM_PROMPT +
                    "[사용자 건강 프로필]
                     - 진단명: ...
                     - 알레르기: ...
                     - 복용 중인 약물: ...
                     ..."
```

---

## 7. Medical Document Upload Flow (Planned)

```
User
 │── POST /medical-documents (multipart/form-data)
 │        file: image.jpg | prescription.pdf
 │
FastAPI
 ├── validate: file_size ≤ 10MB, format in [PNG, JPG, PDF]
 ├── save to local storage: /uploads/{user_id}/{uuid}.{ext}
 ├── create MedicalDocument(status=PENDING)
 └── push OCR task to Redis queue
          │
     AI Worker
          ├── GPT-4o Vision: extract text from image
          ├── structure: medication_name, dosage, frequency
          ├── create OCRResult
          └── update MedicalDocument(status=SUCCESS, confidence_score)
```

> **Note:** Use `multipart/form-data` for file uploads. Do NOT encode images as Base64 in the DB — it inflates row size and degrades query performance. Use local storage first; migrate to AWS S3 when scaling.

---

## 8. Auto Session Title Generation

```
send_message() called
     │
     └── AI Worker: generate_chat_response()
              │
              ├── if payload.history == [] (first message)
              │        └── _generate_title(user_message)
              │                 └── GPT call: "15자 이내 한국어 제목 생성"
              │                          → title: str
              │
              └── ChatTaskResult(answer=..., title=title | None)

FastAPI on result:
     └── if title and not history → session_repo.update_title(session, title)
```

---

## 9. Data Model Relationships

```
User (1)
 ├──(1:1) HealthProfile
 │          └──(1:N) HealthProfileHistory
 │
 ├──(1:N) ChatSession
 │          └──(1:N) ChatMessage
 │
 ├──(1:N) MedicalDocument
 │          └──(1:1) OCRResult
 │
 ├──(1:N) Medication  ──(N:1, nullable)── MedicalDocument
 │
 └──(1:N) HealthGuidance ──(N:1, nullable)── HealthProfile
```

---

## 10. API Endpoint Map

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login (httponly cookie JWT) |
| POST | `/api/v1/auth/logout` | Logout |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/users/me` | Get current user |
| GET | `/api/v1/health-profile` | Get or create health profile |
| PATCH | `/api/v1/health-profile` | Update health profile |
| GET | `/api/v1/health-profile/history` | Profile change history |
| GET | `/api/v1/chat/sessions` | List chat sessions |
| POST | `/api/v1/chat/sessions` | Create session |
| GET | `/api/v1/chat/sessions/{id}` | Session detail + messages |
| DELETE | `/api/v1/chat/sessions/{id}` | Delete session |
| POST | `/api/v1/chat/sessions/{id}/messages` | Send message (sync) |
| POST | `/api/v1/chat/sessions/{id}/messages/stream` | Send message (SSE stream) |
| POST | `/api/v1/medical-documents` | Upload document *(planned)* |
| GET | `/api/v1/medical-documents` | List documents *(planned)* |
| GET | `/api/v1/medications` | List medications *(planned)* |

---

## 11. Technology Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Frontend | React 19 + Vite + TypeScript | Fast HMR, type safety |
| Backend | FastAPI + Python 3.13 | Async-native, auto OpenAPI docs |
| ORM | Tortoise ORM + Aerich | Async ORM, migration support |
| Database | MySQL 8 | Relational data, ACID compliance |
| Cache/Queue | Redis | Task queue + SSE chunk buffer |
| AI | OpenAI GPT-4o-mini (dev) / GPT-4o (prod) | Cost-efficient dev, powerful prod |
| Package mgr | uv | Fast, lockfile-based |
| Linting | ruff | Single tool for lint + format |
| Proxy | Nginx | Static serving + API reverse proxy |
| Container | Docker Compose | Local dev parity |

---

## 12. Environment Configuration

| Variable | Dev | Prod |
|----------|-----|------|
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | `gpt-4o` |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | `text-embedding-3-large` |
| `DEBUG` | `true` | `false` |
| File storage | Local `/uploads` | AWS S3 *(planned)* |
