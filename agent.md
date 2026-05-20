# agent.md — AI Worker Task Processing Rules

Rules for the AI Worker (`ai_worker/`) that processes async tasks from the Redis queue.

---

## Worker Overview

The AI Worker is a separate Python process that:
1. Listens on `ai:chat:queue` (Redis)
2. Processes each task using OpenAI API
3. Pushes results back to Redis for FastAPI to consume

```
ai_worker/
  main.py          ← entry point, Redis loop
  core/
    config.py      ← settings (OPENAI_API_KEY, model names)
    logger.py      ← structured logging
  schemas/
    chats.py       ← Pydantic models for task payload/result
  tasks/
    chat_task.py   ← chat response generation (streaming + non-streaming)
```

---

## Task Payload Contract

Every task pushed to Redis must be a JSON string matching `ChatTaskPayload`:

```python
class ChatTaskPayload(BaseModel):
    task_id: str          # uuid hex — used as result key suffix
    session_id: int
    user_message: str
    history: list[HistoryItem] = []    # last 20 messages max
    health_profile: HealthProfilePayload | None = None
    stream: bool = False
```

Result must match `ChatTaskResult`:

```python
class ChatTaskResult(BaseModel):
    task_id: str
    answer: str
    title: str | None = None   # set only on first message (history=[])
```

---

## System Prompt Rules

Base prompt is always applied. Health profile is injected dynamically.

```
BASE_SYSTEM_PROMPT (always)
  +
[사용자 건강 프로필] section (only if health_profile is not None)
```

### Healthcare Safety Rules (must always be in system prompt)
1. Never recommend stopping medication, self-diagnosis, or changing prescriptions
2. For emergencies, always direct to 119 or hospital immediately
3. For uncertain information, always add: "정확한 진단은 의료 전문가와 상담하시기 바랍니다"
4. Always respond in Korean

---

## Streaming Rules

When `payload.stream == True`:

1. Use `client.chat.completions.create(..., stream=True)`
2. Push each text chunk via `rpush` (right-push, preserves order)
3. FastAPI consumes via `blpop` (left-pop) → correct FIFO order
4. Final sentinel must include:
   ```json
   {"chunk": "", "done": true, "title": "...", "full_text": "..."}
   ```
5. Always set TTL on stream key: `expire(stream_key, 300)`
6. On error, push error sentinel immediately:
   ```json
   {"chunk": "", "done": true, "error": "error message"}
   ```

---

## Title Generation Rules

- Only generate title when `len(payload.history) == 0` (first message)
- Max 15 Korean characters
- Use low temperature (0.3) for deterministic output
- Use `max_tokens=30` to keep it cheap
- Prompt: `"사용자의 첫 질문을 보고 채팅 세션 제목을 15자 이내 한국어로 생성하세요. 제목만 출력하고 다른 내용은 쓰지 마세요."`

---

## Model Selection

Always read from `settings.OPENAI_CHAT_MODEL` — never hardcode:

```python
response = await get_client().chat.completions.create(
    model=settings.OPENAI_CHAT_MODEL,  # gpt-4o-mini (dev) / gpt-4o (prod)
    ...
)
```

---

## Error Handling

```python
try:
    # OpenAI call
except Exception as e:
    logger.error(f"Task failed: {payload.task_id} | {e}")
    # For streaming: push error sentinel to stream key
    # For non-streaming: log and continue loop (do not crash worker)
```

The worker loop must **never crash**. Catch all exceptions at the top level.

---

## Performance Limits

| Parameter | Value | Reason |
|-----------|-------|--------|
| `history` window | Last 20 messages | Token cost control |
| `max_tokens` (chat) | 1024 | Reasonable response length |
| `max_tokens` (title) | 30 | Title is short |
| `temperature` (chat) | 0.7 | Balanced creativity |
| `temperature` (title) | 0.3 | Deterministic output |
| Redis result TTL | 300s | Prevent memory leak |

---

## Adding New Task Types

When adding a new AI task (e.g., OCR, embedding):

1. Add new Pydantic schema to `ai_worker/schemas/`
2. Add new task function to `ai_worker/tasks/<name>_task.py`
3. Add new queue key constant (e.g., `AI_OCR_QUEUE = "ai:ocr:queue"`)
4. Route in `ai_worker/main.py` based on queue key or payload type
5. Add corresponding constants to `app/services/` that push to the same queue key
