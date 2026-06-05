"""약물 데이터 → drug_master 테이블 적재 스크립트.

적재 우선순위:
1. 식약처_의약품개요정보_전체누적본.csv  (필수, 복약가이드 상세 컬럼 포함)
2. all_drugs_master.csv              (선택, 식약처에 없는 전문의약품만 추가)

Usage:
    PYTHONPATH=. DB_HOST=localhost uv run python scripts/load_drug_master.py
"""

import asyncio
import csv
import html
import re
import sys
from pathlib import Path

import asyncpg

from ai_worker.core.config import config

# NB_DOC_DATA 등 긴 텍스트 필드를 위한 csv 필드 크기 제한 확장
# macOS에서 sys.maxsize가 C long 범위를 초과할 수 있어 OverflowError 방어 처리
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2**31 - 1)

DATA_DIR = Path(__file__).parent.parent / "app" / "data"
SHIKCHE_CSV = DATA_DIR / "식약처_의약품개요정보_전체누적본.csv"
MASTER_CSV = DATA_DIR / "all_drugs_master.csv"
BATCH_SIZE = 1000

# INSERT 컬럼 순서 고정
_INSERT_SQL = """
INSERT INTO drug_master
    (item_name, dosage, cautions, side_effects, storage, etc_otc_code, source)
VALUES ($1, $2, $3, $4, $5, $6, $7)
"""


def _clean(val: object) -> str | None:
    """None / 빈 문자열 / 'nan' 을 None으로 정규화."""
    v = str(val).strip() if val is not None else ""
    return v if v and v.lower() != "nan" else None


def _strip_html(text: str) -> str:
    """HTML 태그·엔티티 제거 후 공백 정리."""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _read_shikche() -> dict[str, tuple]:
    """식약처 CSV → item_name 기준 dict 반환.

    반환 tuple 순서: (item_name, dosage, cautions, side_effects, storage, etc_otc_code, source)
    """
    rows: dict[str, tuple] = {}
    with open(SHIKCHE_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = _clean(row.get("itemName"))
            if not name:
                continue
            name = name[:255]

            caution_parts = [
                _clean(row.get("atpnWarnQesitm")) or "",
                _clean(row.get("atpnQesitm")) or "",
                _clean(row.get("intrcQesitm")) or "",
            ]
            cautions = "\n\n".join(p for p in caution_parts if p) or None

            rows[name] = (
                name,
                _clean(row.get("useMethodQesitm")),  # dosage
                cautions,  # cautions
                _clean(row.get("seQesitm")),  # side_effects
                _clean(row.get("depositMethodQesitm")),  # storage
                None,  # etc_otc_code (식약처 CSV 없음)
                "식약처",  # source
            )
    return rows


def _read_master(existing_names: set[str]) -> list[tuple]:
    """all_drugs_master.csv → 식약처에 없는 약물만 list 반환.

    반환 tuple 순서: (item_name, dosage, cautions, side_effects, storage, etc_otc_code, source)
    """
    rows: list[tuple] = []
    with open(MASTER_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = _clean(row.get("ITEM_NAME"))
            if not name or name in existing_names:
                continue
            name = name[:255]
            existing_names.add(name)

            dosage_raw = _clean(row.get("UD_DOC_DATA")) or ""
            cautions_raw = _clean(row.get("NB_DOC_DATA")) or ""

            rows.append(
                (
                    name,
                    _strip_html(dosage_raw) or None,  # dosage
                    _strip_html(cautions_raw) or None,  # cautions
                    None,  # side_effects (master CSV 없음)
                    None,  # storage (master CSV 없음)
                    _clean(row.get("ETC_OTC_CODE")),  # etc_otc_code
                    "제품허가정보",  # source
                )
            )
    return rows


async def load() -> None:
    # ── 1. 식약처 CSV 읽기 (필수) ─────────────────────────────────────────────
    if not SHIKCHE_CSV.exists():
        print(f"[오류] 필수 파일 없음: {SHIKCHE_CSV}", file=sys.stderr)
        sys.exit(1)

    print(f"식약처 CSV 읽는 중: {SHIKCHE_CSV.name}")
    shikche_rows = _read_shikche()
    print(f"  → {len(shikche_rows):,}개")

    all_rows: list[tuple] = list(shikche_rows.values())
    existing_names: set[str] = set(shikche_rows.keys())

    # ── 2. all_drugs_master.csv 읽기 (선택) ──────────────────────────────────
    if MASTER_CSV.exists():
        print("all_drugs_master.csv 읽는 중 (식약처 미포함 약물만)...")
        master_rows = _read_master(existing_names)
        print(f"  → 추가 {len(master_rows):,}개")
        all_rows.extend(master_rows)
    else:
        print("all_drugs_master.csv 없음 → skip")

    print(f"총 적재 대상: {len(all_rows):,}개")

    # ── 3. DB 적재 ────────────────────────────────────────────────────────────
    conn = await asyncpg.connect(config.DATABASE_URL)
    try:
        await conn.execute("TRUNCATE TABLE drug_master RESTART IDENTITY")
        for i in range(0, len(all_rows), BATCH_SIZE):
            batch = all_rows[i : i + BATCH_SIZE]
            await conn.executemany(_INSERT_SQL, batch)
            done = min(i + BATCH_SIZE, len(all_rows))
            print(f"  {done:,} / {len(all_rows):,} 적재 중...", end="\r")
    finally:
        await conn.close()

    print(f"\n완료: {len(all_rows):,}개 적재")


if __name__ == "__main__":
    asyncio.run(load())
