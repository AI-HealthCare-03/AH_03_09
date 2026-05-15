from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core import config

_pool: ConnectionPool | None = None


def init_db() -> None:
    global _pool
    _pool = ConnectionPool(
        conninfo=config.DATABASE_URL,
        min_size=2,
        max_size=10,
        kwargs={"row_factory": dict_row},
    )


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("DB pool이 초기화되지 않았습니다. init_db()를 먼저 호출하세요.")
    return _pool
