# CLAUDE.md — AI Healthcare Platform

This file is automatically loaded by Claude Code. Follow every rule here without exception.

---

## Project Overview

AI-powered healthcare assistant backend built with FastAPI.
Architecture: **React (frontend) → Nginx → FastAPI → Redis → AI Worker → OpenAI**

---

## Non-Negotiable Rules

### 1. Always Plan Before Coding
- For any non-trivial task, write a brief plan (what files change, why) and get confirmation before editing.
- Never touch more than 3 files at once without explicit user approval.

### 2. Branch Strategy
```
main        ← stable, production-ready
  └── develop      ← integration branch
        └── feature/<name>   ← one feature per branch
```
- Always branch from `develop`, never from `main`.
- Commit to the feature branch, merge into `develop`, push to remote `my`.

### 3. Never Commit Secrets
- `.env` is gitignored. Never hardcode API keys, passwords, or tokens in any file.
- If you see a secret in a file, remove it immediately and warn the user.

---

## Python Standards

| Item | Rule |
|------|------|
| Version | Python **3.13** |
| Package manager | **uv** (never pip install directly) |
| Linter / Formatter | **ruff** (`ruff check`, `ruff format`) |
| Style guide | [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) |
| Test framework | **pytest** |
| Type hints | Required on all function signatures |
| Docstrings | Only when WHY is non-obvious. No multi-line docstrings for simple functions. |

### Ruff Config (pyproject.toml)
```toml
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

---

## FastAPI Architecture

Strict layered architecture — **no skipping layers**:

```
Router  →  Service  →  Repository  →  Model (Tortoise ORM)
```

- **Router**: HTTP only. No business logic. Thin as possible.
- **Service**: Business logic. Calls repositories. Raises `HTTPException`.
- **Repository**: DB queries only. No business logic. Returns ORM model instances.
- **Model**: Tortoise ORM. Table definitions and enums only.

### File Naming
```
app/
  apis/v1/      → <domain>_routers.py
  services/     → <domain>.py  (plural for domain, e.g. chats.py)
  repositories/ → <domain>_repository.py
  models/       → <domain>.py
  dtos/         → <domain>.py
```

### Response Pattern
```python
# Always use ORJSONResponse for JSON endpoints
from fastapi.responses import ORJSONResponse as Response

@router.get("", response_model=SomeResponse)
async def handler(...) -> Response:
    result = await service.do_something()
    return Response(SomeResponse.model_validate(result).model_dump())
```

---

## Database Rules

- ORM: **Tortoise ORM** with **Aerich** for migrations
- Always run `aerich migrate` + `aerich upgrade` after model changes
- Use `in_transaction()` for multi-step writes
- Never use raw SQL unless absolutely necessary
- All models must have `created_at` (auto_now_add=True)
- Update-able models must have `updated_at` (auto_now=True)

---

## Redis Queue Pattern

```
FastAPI                Redis                  AI Worker
  lpush(queue, task) ──▶ blpop(queue) ──▶ process
  blpop(result_key)  ◀── lpush(result_key) ──
```

- Non-streaming: `ai:chat:queue` → `ai:chat:result:{task_id}`
- Streaming: `ai:chat:queue` (stream=True) → `ai:chat:stream:{task_id}` (rpush chunks)
- All Redis keys must have TTL set (`expire`)

---

## File Upload Rules

- Use `multipart/form-data` — never Base64 encode files in DB
- Max file size: **10MB** (validate in service layer)
- Allowed formats: PNG, JPG, PDF
- Storage: local `/uploads/{user_id}/{uuid}.{ext}` for dev; S3 for prod
- Save file path in DB, not file content

---

## OpenAI Model Policy

| Environment | Chat Model | Embedding Model |
|-------------|-----------|-----------------|
| Development | `gpt-4o-mini` | `text-embedding-3-small` |
| Production | `gpt-4o` | `text-embedding-3-large` |

Always read from `settings.OPENAI_CHAT_MODEL` — never hardcode model names.

---

## Code Style Rules

- **No comments** unless the WHY is non-obvious
- **No unused imports** — ruff will catch these
- **No `print()`** — use `logger.info/error` from `app/core/logger.py`
- **No mutable default arguments** (e.g. `def f(x=[])`)
- Prefer `async/await` over sync for all I/O
- Use `model_dump()` not `.dict()` (Pydantic v2)
- Use `model_validate()` not `.from_orm()` (Pydantic v2)

---

## Testing

```bash
pytest app/tests/          # run all tests
pytest app/tests/ -v       # verbose
pytest app/tests/ -k "chat" # filter by name
```

- Test file naming: `test_<module>.py`
- One test file per router/service module
- Do NOT mock the database in integration tests

---

## Commit Message Format

```
<emoji> <type>: <short description>

✨ feat    → new feature
🐛 fix     → bug fix
♻️ refactor → code restructure
📝 docs    → documentation only
⚙️ chore   → config, build, deps
🔀 merge   → merge commit
```

Always add at the end:
```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```
