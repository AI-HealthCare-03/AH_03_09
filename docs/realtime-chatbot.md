# 실시간 건강 챗봇 구조 정리

## 아키텍처

```
Client (fetch + ReadableStream)
    ↕  POST /api/v1/chat/sessions/{id}/messages/stream
FastAPI (StreamingResponse)
    ↓ Redis lpush  →  ai:chat:queue
Redis Queue
    ↓ blpop
AI Worker
    ├── Phase 1: 툴 선택 (tool_choice="auto", 비스트리밍)
    ├── Phase 2: 툴 실행 (get_health_profile / get_prescription_guide / search_drug_info)
    └── Phase 3: GPT-4o-mini 스트리밍 → Redis rpush  →  ai:chat:stream:{task_id}
FastAPI
    └── Redis blpop  →  NDJSON 청크 스트리밍 응답
```

## 메시지 흐름

1. 클라이언트 → `POST /messages/stream` 로 메시지 전송
2. FastAPI → DB에 유저 메시지 저장
3. FastAPI → Redis `ai:chat:queue` 에 task 발행
4. AI Worker → Redis blpop으로 task 수신
5. AI Worker → Phase 1: LLM이 필요한 툴 결정
6. AI Worker → Phase 2: 툴 실행 후 컨텍스트 구성
7. AI Worker → Phase 3: GPT-4o-mini 스트리밍 호출, 토큰마다 `ai:chat:stream:{task_id}` 에 rpush
8. FastAPI → Redis blpop으로 청크 수신 후 NDJSON으로 클라이언트에 전달
9. AI Worker → `[DONE]` 발행으로 완료 신호
10. FastAPI → DB에 전체 응답 저장

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/v1/chat/sessions` | 새 채팅 세션 생성 |
| `GET` | `/api/v1/chat/sessions` | 내 세션 목록 조회 |
| `GET` | `/api/v1/chat/sessions/{id}` | 세션 상세 + 메시지 목록 |
| `DELETE` | `/api/v1/chat/sessions/{id}` | 세션 삭제 |
| `GET` | `/api/v1/chat/sessions/{id}/messages` | 세션 메시지 히스토리 |
| `POST` | `/api/v1/chat/sessions/{id}/messages` | 메시지 전송 (동기, Swagger 테스트용) |
| `POST` | `/api/v1/chat/sessions/{id}/messages/stream` | 메시지 전송 (HTTP Streaming) |
| `PATCH` | `/api/v1/chat/sessions/{id}/messages/{msg_id}/feedback` | 메시지 피드백 (좋아요/싫어요) |

## HTTP Streaming 메시지 포맷 (NDJSON)

### 클라이언트 → 서버
```json
{
  "content": "안녕하세요, 두통이 심한데 어떻게 해야 하나요?",
  "guide_id": "optional-guide-uuid"
}
```

### 서버 → 클라이언트 (줄 단위 JSON)
```json
// 스트리밍 청크 (응답 생성 중)
{"type": "chunk", "chunk": "두통이"}

// 응답 완료
{"type": "done", "content": "두통이 심하시다면..."}

// 오류 발생
{"type": "error", "detail": "에러 메시지"}
```

## 스킬 시스템 (LLM 하네스)

AI Worker는 사용자 메시지를 6개 스킬로 분류해 맞춤 프롬프트를 적용합니다.

| 스킬 | 설명 |
|------|------|
| `EMERGENCY` | 응급 증상 판단, 119 신고 기준 안내 |
| `DRUG_INTERACTION` | 약물 간 상호작용 분석 |
| `SIDE_EFFECT` | 부작용 증상 판단 및 권장 행동 |
| `MEDICATION_GUIDE` | 복용법, 용량, 특수 상황(임신부/수유부/노인) 안내 |
| `DISEASE_INQUIRY` | 처방전 질병코드·건강 프로필 기반 질병 정보 안내 |
| `GENERAL` | 기본 복약 관리 어시스턴트 |

## 툴 콜링 (3-Phase)

**Phase 1** — LLM이 필요한 데이터 결정 (비스트리밍, max_tokens=200)
**Phase 2** — 툴 실행

| 툴 | 역할 |
|------|------|
| `get_health_profile` | 건강 프로필 (기저질환, 알레르기, 복용 약물) |
| `get_prescription_guide` | 처방전 기반 가이드 (처방약, 질병코드, 복약 일정) |
| `search_drug_info` | 식약처 DB 약물 상세 검색 (RAG) |

**Phase 3** — 툴 결과 포함 최종 스트리밍 응답 (max_tokens=600)

## 신규 파일 목록

### FastAPI (app/)
| 파일 | 설명 |
|------|------|
| `app/models/chat.py` | ChatSession, ChatMessage ORM 모델 |
| `app/dtos/chat.py` | Request/Response DTO |
| `app/repositories/chat_repository.py` | DB 접근 레이어 |
| `app/services/chat.py` | 비즈니스 로직 + HTTP Streaming 핸들러 |
| `app/apis/v1/chat_routers.py` | HTTP 라우터 |
| `app/core/redis_client.py` | Redis 비동기 클라이언트 |

### AI Worker (ai_worker/)
| 파일 | 설명 |
|------|------|
| `ai_worker/schemas/chat.py` | ChatTaskPayload Pydantic 모델 |
| `ai_worker/core/llm.py` | OpenAI 클라이언트 + 스킬 시스템 + 툴 콜링 |
| `ai_worker/tasks/chat_task.py` | GPT-4o-mini 호출 및 Redis 발행 |
| `ai_worker/main.py` | Worker 진입점 (Redis blpop 루프) |

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
uv run alembic upgrade head

# 3. AI Worker 코드 변경 시 재시작 (재빌드 불필요)
docker compose restart ai-worker

# 4. HTTP Streaming 테스트 (curl)
# 먼저 POST /api/v1/auth/login 으로 access_token 획득
# 그 다음 POST /api/v1/chat/sessions 으로 session_id 획득
curl -N -X POST "http://localhost/api/v1/chat/sessions/{session_id}/messages/stream" \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"content": "타이레놀 복용법 알려줘"}'

# 5. AI Worker 로그 확인
docker compose logs -f ai-worker
```
