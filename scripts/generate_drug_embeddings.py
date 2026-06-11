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
from math import ceil

import asyncpg
from openai import AsyncOpenAI

sys.path.insert(0, ".")
from app.core.config import config  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_EMBED_MODEL = "text-embedding-3-small"
_BATCH_SIZE = 100
_IVFFLAT_LISTS = 100


def _drug_to_text(row: asyncpg.Record) -> str:
    parts = [row["item_name"]]
    if row["dosage"]:
        parts.append(f"용법: {row['dosage'][:300]}")
    if row["side_effects"]:
        parts.append(f"부작용: {row['side_effects'][:300]}")
    if row["cautions"]:
        parts.append(f"주의사항: {row['cautions'][:300]}")
    return ". ".join(parts)


async def main() -> None:
    if not config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    conn = await asyncpg.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
    )

    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

        rows = await conn.fetch(
            "SELECT id, item_name, dosage, side_effects, cautions FROM drug_master WHERE embedding IS NULL ORDER BY id"
        )
        total = len(rows)
        logger.info("임베딩 미생성 항목: %d건", total)

        if total == 0:
            logger.info("모든 항목이 이미 임베딩 완료 상태입니다.")
        else:
            batches = ceil(total / _BATCH_SIZE)
            processed = 0

            for i in range(batches):
                batch = rows[i * _BATCH_SIZE : (i + 1) * _BATCH_SIZE]
                texts = [_drug_to_text(r) for r in batch]

                resp = await client.embeddings.create(model=_EMBED_MODEL, input=texts)
                embeddings = [e.embedding for e in resp.data]

                await conn.executemany(
                    "UPDATE drug_master SET embedding = $1::vector WHERE id = $2",
                    [
                        ("[" + ",".join(str(v) for v in emb) + "]", r["id"])
                        for emb, r in zip(embeddings, batch, strict=False)
                    ],
                )
                processed += len(batch)
                logger.info("진행: %d / %d (%.1f%%)", processed, total, processed / total * 100)

        # IVFFlat 인덱스: 임베딩 있는 행 수에 맞게 lists 조정
        embed_count = await conn.fetchval("SELECT COUNT(*) FROM drug_master WHERE embedding IS NOT NULL")
        if embed_count == 0:
            logger.warning("임베딩 데이터 없음 — 인덱스 생성 건너뜀")
            return

        lists = min(_IVFFLAT_LISTS, max(1, embed_count // 50))
        logger.info("IVFFlat 인덱스 생성 중 (lists=%d, rows=%d)...", lists, embed_count)
        await conn.execute(
            f"CREATE INDEX IF NOT EXISTS ix_drug_master_embedding_ivfflat "
            f"ON drug_master USING ivfflat (embedding vector_cosine_ops) "
            f"WITH (lists = {lists})"
        )
        logger.info("완료!")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
