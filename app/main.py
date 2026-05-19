from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from tortoise import Tortoise

from app.apis.v1 import v1_routers
from app.core import config
from app.core.db.databases import TORTOISE_ORM
from app.core.db.sqlalchemy_client import _engine
from app.models.ocr.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await Tortoise.close_connections()


app = FastAPI(
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_routers)
