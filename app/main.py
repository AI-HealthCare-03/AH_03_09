import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.apis.v1 import v1_routers
from app.core import config
from app.core.cleanup import run_cleanup_loop
from app.core.db.sqlalchemy_client import close_db
from app.core.redis_client import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(run_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        await close_redis()
        await close_db()


app = FastAPI(
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        config.FRONTEND_URL,
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_routers)
