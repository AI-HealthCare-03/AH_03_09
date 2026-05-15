# 실시간 건강 챗봇 구조 정리

## 아키텍처

```
Client (WebSocket)
    ↕  ws://host/api/v1/chat/ws/{session_id}?token=<JWT>
FastAPI (WebSocket Manager)
    ↓ Redis Publish  →  chat:request:{session_id}
Redis Pub/Sub
    ↓ Subscribe (psubscribe "chat:request:*")
AI Worker
    ├── GPT-4o-mini 스트리밍 호출
    └── 토큰마다 Publish  →  chat:stream:{session_id}
FastAPI
    └── Redis Subscribe  →  WebSocket으로 토큰 전달
```

## 메시지 흐름

1. 클라이언트 → WebSocket 메시지 전송
2. FastAPI → DB에 유저 메시지 저장
3. FastAPI → Redis `chat:request:{session_id}` 에 task 발행
4. AI Worker → Redis 구독, GPT-4o-mini 스트리밍 호출
5. AI Worker → 각 토큰을 `chat:stream:{session_id}` 에 발행
6. FastAPI → Redis 토큰 수신 후 WebSocket으로 전달
7. AI Worker → `[DONE]` 발행으로 완료 신호
8. FastAPI → DB에 전체 응답 저장, 클라이언트에 `done` 이벤트 전송

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/v1/chat/sessions` | 새 채팅 세션 생성 |
| `GET` | `/api/v1/chat/sessions` | 내 세션 목록 조회 |
| `GET` | `/api/v1/chat/sessions/{id}/messages` | 세션 메시지 히스토리 |
| `WS` | `/api/v1/chat/ws/{session_id}?token=<JWT>` | 실시간 채팅 |

## WebSocket 메시지 포맷

### 클라이언트 → 서버
```
"안녕하세요, 두통이 심한데 어떻게 해야 하나요?"
```
*(일반 텍스트)*

### 서버 → 클라이언트
```json
// 스트리밍 토큰 (응답 생성 중)
{"type": "stream", "content": "두통이"}

// 응답 완료
{"type": "done", "content": "두통이 심하시다면..."}

// 오류 발생
{"type": "error", "content": "에러 메시지"}
```

## 신규 파일 목록

### FastAPI (app/)
| 파일 | 설명 |
|------|------|
| `app/models/chat.py` | ChatSession, ChatMessage ORM 모델 |
| `app/dtos/chat.py` | Request/Response DTO |
| `app/repositories/chat_repository.py` | DB 접근 레이어 |
| `app/services/chat.py` | 비즈니스 로직 + WebSocket 핸들러 |
| `app/apis/v1/chat_routers.py` | HTTP + WebSocket 라우터 |
| `app/core/redis_client.py` | Redis 비동기 클라이언트 |

### AI Worker (ai_worker/)
| 파일 | 설명 |
|------|------|
| `ai_worker/schemas/chat.py` | ChatTaskPayload Pydantic 모델 |
| `ai_worker/core/llm.py` | OpenAI 클라이언트 + 스트리밍 함수 |
| `ai_worker/tasks/chat_task.py` | GPT-4o-mini 호출 및 Redis 발행 |
| `ai_worker/main.py` | Worker 진입점 (Redis psubscribe 루프) |

## 인프라 변경 사항

- **DB**: MySQL → PostgreSQL (`pgvector/pgvector:pg16`)
- **패키지**: `asyncmy` → `asyncpg`, `openai>=1.82.0` 추가

## 환경 변수 (.env)

```env
# PostgreSQL
DB_HOST=postgres
DB_PORT=5432
DB_USER=ai_health
DB_PASSWORD=ai_health_pw
DB_NAME=ai_health_db

# Redis
REDIS_URL=redis://redis:6379

# OpenAI
OPENAI_API_KEY=your-actual-api-key
```

## 실행 방법

```bash
# 1. Docker 기동
docker compose up -d

# 2. DB 마이그레이션 (최초 1회)
uv run aerich migrate
uv run aerich upgrade

# 3. WebSocket 테스트 (wscat 사용)
# 먼저 POST /api/v1/auth/login 으로 access_token 획득
# 그 다음 POST /api/v1/chat/sessions 으로 session_id 획득
wscat -c "ws://localhost/api/v1/chat/ws/{session_id}?token={access_token}"

# 4. AI Worker 로그 확인
docker compose logs -f ai-worker
```

## 시스템 프롬프트

AI Worker (`ai_worker/core/llm.py`)에 하드코딩된 건강 챗봇 페르소나:

```
당신은 친절하고 전문적인 건강 상담 챗봇입니다.
- 건강, 영양, 운동, 의약품에 관한 질문에 성실히 답변합니다.
- 의학적 진단은 제공할 수 없으며, 심각한 증상은 반드시 전문의 상담을 권유합니다.
- 모든 답변은 한국어로 합니다.
- 과학적 근거가 있는 정보를 바탕으로 답변합니다.
```
