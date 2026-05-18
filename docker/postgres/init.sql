-- 컨테이너 최초 기동 시 자동 실행: PostgreSQL 확장만 설치.
-- 테이블 스키마는 FastAPI 기동 시 Tortoise.generate_schemas() 가 자동으로 생성한다.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
