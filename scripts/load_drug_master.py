"""식약처 CSV → drug_master 테이블 적재 스크립트.

Usage:
    uv run python scripts/load_drug_master.py
"""

import asyncio
import csv
import sys
from pathlib import Path

import asyncpg

from ai_worker.core.config import config

CSV_PATH = Path(__file__).parent.parent / "data" / "drugs.csv"
BATCH_SIZE = 1000


async def load() -> None:
    conn = await asyncpg.connect(config.DATABASE_URL)

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        item_names = [row["itemName"].strip() for row in reader if row.get("itemName", "").strip()]

    item_names = list(dict.fromkeys(item_names))

    await conn.execute("TRUNCATE TABLE drug_master RESTART IDENTITY")
    for i in range(0, len(item_names), BATCH_SIZE):
        batch = item_names[i : i + BATCH_SIZE]
        await conn.executemany("INSERT INTO drug_master (item_name) VALUES ($1)", [(n,) for n in batch])
        print(f"  {min(i + BATCH_SIZE, len(item_names))} / {len(item_names)} 적재 중...", end="\r")

    await conn.close()
    print(f"\n완료: {len(item_names)}개 약물명 적재")


if __name__ == "__main__":
    if not CSV_PATH.exists():
        print(f"CSV 파일 없음: {CSV_PATH}", file=sys.stderr)
        sys.exit(1)
    asyncio.run(load())
