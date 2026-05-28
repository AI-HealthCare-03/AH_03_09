"""식약처 CSV → drug_master 테이블 적재 스크립트.

두 파일을 합쳐 중복 제거 후 적재합니다:
- data/drugs.csv          : 일반의약품 (itemName 컬럼)
- data/all_drugs_item_names.csv : 전문+일반의약품 전체 (ITEM_NAME 컬럼)

Usage:
    PYTHONPATH=. DB_HOST=localhost uv run python scripts/load_drug_master.py
"""

import asyncio
import csv
import sys
from pathlib import Path

import asyncpg

from ai_worker.core.config import config

DATA_DIR = Path(__file__).parent.parent / "data"
BATCH_SIZE = 1000


def _read_csv(path: Path, col: str) -> set[str]:
    names: set[str] = set()
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get(col) or "").strip()[:255]
            if name:
                names.add(name)
    return names


async def load() -> None:
    names: set[str] = set()

    p1 = DATA_DIR / "drugs.csv"
    if p1.exists():
        n1 = _read_csv(p1, "itemName")
        print(f"drugs.csv: {len(n1)}개")
        names |= n1

    p2 = DATA_DIR / "all_drugs_item_names.csv"
    if p2.exists():
        n2 = _read_csv(p2, "ITEM_NAME")
        print(f"all_drugs_item_names.csv: {len(n2)}개")
        names |= n2

    if not names:
        print("CSV 파일 없음 또는 데이터 없음", file=sys.stderr)
        sys.exit(1)

    item_names = sorted(names)
    print(f"중복 제거 후: {len(item_names)}개")

    conn = await asyncpg.connect(config.DATABASE_URL)
    await conn.execute("TRUNCATE TABLE drug_master RESTART IDENTITY")
    for i in range(0, len(item_names), BATCH_SIZE):
        batch = item_names[i : i + BATCH_SIZE]
        await conn.executemany("INSERT INTO drug_master (item_name) VALUES ($1)", [(n,) for n in batch])
        print(f"  {min(i + BATCH_SIZE, len(item_names))} / {len(item_names)} 적재 중...", end="\r")
    await conn.close()
    print(f"\n완료: {len(item_names)}개 약물명 적재")


if __name__ == "__main__":
    asyncio.run(load())
