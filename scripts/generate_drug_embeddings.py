"""
drug_master 전체 임베딩 생성 스크립트

Usage:
    PYTHONPATH=. uv run python scripts/generate_drug_embeddings.py

- drug_master.embedding IS NULL 인 행을 배치로 처리
- OpenAI text-embedding-3-small (1536dims) 임베딩 생성
- 완료 후 IVFFlat 인덱스 생성 (코사인 거리)
"""

import asyncio
import logging
import sys

import asyncpg
from openai import AsyncOpenAI

sys.path.insert(0, ".")
from app.core.config import Config  # noqa: E402

config = Config()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_EMBED_MODEL = "text-embedding-3-small"
_BATCH_SIZE = 20
_BATCH_SLEEP = 1.0  # 배치 간 딜레이 (초) — DB 메모리 압박 방지


def _drug_to_text(row: asyncpg.Record) -> str:
    parts = [row["item_name"]]
    if row["dosage"]:
        parts.append(f"용법: {row['dosage'][:300]}")
    if row["side_effects"]:
        parts.append(f"부작용: {row['side_effects'][:300]}")
    if row["cautions"]:
        parts.append(f"주의사항: {row['cautions'][:300]}")
    return ". ".join(parts)


DB_CONNECT_ARGS = dict(
    host=config.DB_HOST,
    port=config.DB_PORT,
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    database=config.DB_NAME,
)


async def _connect() -> asyncpg.Connection:
    for attempt in range(10):
        try:
            conn = await asyncpg.connect(**DB_CONNECT_ARGS)
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            return conn
        except Exception as e:
            logger.warning("DB 연결 실패 (%d/10): %s — 10초 후 재시도", attempt + 1, e)
            await asyncio.sleep(10)
    raise RuntimeError("DB 연결 10회 실패")


async def main() -> None:
    if not config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    conn = await _connect()

    try:
        total = await conn.fetchval("SELECT COUNT(*) FROM drug_master WHERE embedding IS NULL")
        logger.info("임베딩 미생성 항목: %d건", total)

        if total == 0:
            logger.info("모든 항목이 이미 임베딩 완료 상태입니다.")
        else:
            processed = 0
            last_id = 0

            while True:
                # 연결 끊김 시 재연결
                if conn.is_closed():
                    logger.warning("DB 연결 끊김 — 재연결 시도")
                    conn = await _connect()

                try:
                    batch = await conn.fetch(
                        "SELECT id, item_name, dosage, side_effects, cautions FROM drug_master "
                        "WHERE embedding IS NULL AND id > $1 ORDER BY id LIMIT $2",
                        last_id,
                        _BATCH_SIZE,
                    )
                except Exception:
                    logger.warning("fetch 실패 — 재연결 후 재시도")
                    conn = await _connect()
                    continue

                if not batch:
                    break

                texts = [_drug_to_text(r) for r in batch]
                resp = await client.embeddings.create(model=_EMBED_MODEL, input=texts)
                embeddings = [e.embedding for e in resp.data]

                try:
                    for emb, r in zip(embeddings, batch, strict=False):
                        vec_str = "[" + ",".join(str(v) for v in emb) + "]"
                        await conn.execute(
                            f"UPDATE drug_master SET embedding = '{vec_str}' WHERE id = $1",
                            r["id"],
                        )
                except Exception:
                    logger.warning("update 실패 — 재연결 후 다음 배치 재시도")
                    conn = await _connect()
                    continue

                processed += len(batch)
                last_id = batch[-1]["id"]
                logger.info("진행: %d / %d (%.1f%%)", processed, total, processed / total * 100)
                await asyncio.sleep(_BATCH_SLEEP)

        logger.info("임베딩 생성 완료!")

    finally:
        if not conn.is_closed():
            await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
