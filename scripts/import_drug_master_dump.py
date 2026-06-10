"""drug_master_dump.sql → drug_master 테이블 적재 스크립트.

SQL COPY 포맷을 파싱해 기존 데이터를 교체합니다 (TRUNCATE + INSERT).
중복 방지를 위해 항상 TRUNCATE 후 재적재합니다.

Usage:
    # 덤프 파일 경로 지정
    PYTHONPATH=. uv run python scripts/import_drug_master_dump.py /path/to/drug_master_dump.sql

    # 기본 경로 (app/data/drug_master_dump.sql)
    PYTHONPATH=. uv run python scripts/import_drug_master_dump.py
"""

import asyncio
import sys
from pathlib import Path

import asyncpg

from ai_worker.core.config import config

DEFAULT_DUMP = Path(__file__).parent.parent / "app" / "data" / "drug_master_dump.sql"
BATCH_SIZE = 500

_INSERT_SQL = """
INSERT INTO drug_master (id, item_name, dosage, cautions, side_effects, storage, etc_otc_code, source)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
"""


def _parse_dump(path: Path) -> list[tuple]:
    """COPY public.drug_master ... FROM stdin; 포맷 파싱.

    탭 구분, \\N → None, \\. 으로 데이터 종료.
    """
    rows: list[tuple] = []
    in_copy = False

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            if not in_copy:
                if line.startswith("COPY ") and "drug_master" in line and "FROM stdin" in line:
                    in_copy = True
                continue

            if line == "\\.":
                break

            parts = line.split("\t")
            if len(parts) != 8:
                continue

            def _val(v: str) -> str | int | None:
                return None if v == "\\N" else v

            row_id = parts[0]
            try:
                parsed_id = int(row_id) if row_id != "\\N" else None
            except ValueError:
                continue

            rows.append(
                (
                    parsed_id,  # id
                    _val(parts[1]),  # item_name
                    _val(parts[2]),  # dosage
                    _val(parts[3]),  # cautions
                    _val(parts[4]),  # side_effects
                    _val(parts[5]),  # storage
                    _val(parts[6]),  # etc_otc_code
                    _val(parts[7]),  # source
                )
            )

    return rows


async def load(dump_path: Path) -> None:
    print(f"덤프 파일 파싱 중: {dump_path.name}")
    rows = _parse_dump(dump_path)
    if not rows:
        print("[오류] 파싱된 행이 없습니다. 파일 형식을 확인하세요.", file=sys.stderr)
        sys.exit(1)
    print(f"  → {len(rows):,}개 행 파싱 완료")

    conn = await asyncpg.connect(config.DATABASE_URL)
    try:
        print("기존 데이터 초기화 중 (TRUNCATE)...")
        await conn.execute("TRUNCATE TABLE drug_master RESTART IDENTITY")

        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            await conn.executemany(_INSERT_SQL, batch)
            print(f"  {min(i + BATCH_SIZE, len(rows)):,} / {len(rows):,} 적재 중...", end="\r")

        # id 시퀀스를 최대값 이후로 재설정 (향후 자동증가 충돌 방지)
        await conn.execute("SELECT setval(pg_get_serial_sequence('drug_master', 'id'), MAX(id)) FROM drug_master")
    finally:
        await conn.close()

    print(f"\n완료: {len(rows):,}개 적재")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DUMP
    if not path.exists():
        print(f"[오류] 파일 없음: {path}", file=sys.stderr)
        print("사용법: uv run python scripts/import_drug_master_dump.py <dump_file_path>")
        sys.exit(1)
    asyncio.run(load(path))
