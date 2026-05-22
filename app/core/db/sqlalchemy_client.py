from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import config

_engine = create_async_engine(
    config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=(config.ENV == "local"),
    pool_size=config.DB_CONNECTION_POOL_MINSIZE,
    max_overflow=config.DB_CONNECTION_POOL_MAXSIZE - config.DB_CONNECTION_POOL_MINSIZE,
)

_AsyncSessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with _AsyncSessionFactory() as session:
        yield session


async def close_db() -> None:
    await _engine.dispose()
