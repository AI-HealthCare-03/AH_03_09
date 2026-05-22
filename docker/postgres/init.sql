-- 컨테이너 최초 기동 시 자동 실행 (postgres_data 볼륨이 비어있을 때)
-- 테이블은 FastAPI 기동 시 아래 두 단계로 생성됨:
--   1. Tortoise.generate_schemas()  → users, chat_sessions, chat_messages
--   2. SQLAlchemy Base.metadata.create_all()  → ocr_* 테이블

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
