from fastapi import APIRouter

from app.apis.v1.auth_routers import auth_router
from app.apis.v1.chat_routers import chat_router
from app.apis.v1.user_routers import user_router
from app.core import config
from app.core.config import Env

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(auth_router)
v1_routers.include_router(user_router)
v1_routers.include_router(chat_router)

# Swagger UI에서 가짜 데이터로 로그인/채팅을 테스트하기 위한 dev 라우터.
# 운영 환경에서는 노출하지 않는다.
if config.ENV != Env.PROD:
    from app.apis.v1.dev_routers import dev_router

    v1_routers.include_router(dev_router)
