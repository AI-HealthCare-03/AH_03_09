from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import JSONResponse as Response

from app.core import config
from app.core.config import Env
from app.services.auth import AuthService
from app.services.jwt import JwtService

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.get("/kakao/login", status_code=status.HTTP_200_OK)
async def kakao_login_url(
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    url = auth_service.get_kakao_auth_url()
    return Response(content={"auth_url": url}, status_code=status.HTTP_200_OK)


@auth_router.post("/kakao/callback", status_code=status.HTTP_200_OK)
async def kakao_callback(
    code: str,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    tokens = await auth_service.kakao_login(code)
    resp = Response(
        content={"access_token": str(tokens["access_token"])},
        status_code=status.HTTP_200_OK,
    )
    resp.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        httponly=True,
        secure=config.ENV == Env.PROD,
        domain=config.COOKIE_DOMAIN or None,
        expires=tokens["refresh_token"].payload["exp"],
        samesite="lax",
    )
    return resp


@auth_router.get("/token/refresh", status_code=status.HTTP_200_OK)
async def token_refresh(
    jwt_service: Annotated[JwtService, Depends(JwtService)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token이 없습니다.")
    access_token = jwt_service.refresh_jwt(refresh_token)
    return Response(
        content={"access_token": str(access_token)},
        status_code=status.HTTP_200_OK,
    )
