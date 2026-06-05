from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import JSONResponse as Response

from app.core import config
from app.core.config import Env
from app.services.auth import AuthService
from app.services.jwt import JwtService

auth_router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_OPTS = {
    "httponly": True,
    "samesite": "lax",
}


def _set_access_cookie(resp: Response, access_token: object) -> None:
    resp.set_cookie(
        key="access_token",
        value=str(access_token),
        secure=config.ENV == Env.PROD,
        domain=config.COOKIE_DOMAIN or None,
        **_COOKIE_OPTS,
    )


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
        content={"is_onboarded": tokens["is_onboarded"]},
        status_code=status.HTTP_200_OK,
    )
    _set_access_cookie(resp, tokens["access_token"])
    resp.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        secure=config.ENV == Env.PROD,
        domain=config.COOKIE_DOMAIN or None,
        expires=tokens["refresh_token"].payload["exp"],
        **_COOKIE_OPTS,
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
    resp = Response(content={"ok": True}, status_code=status.HTTP_200_OK)
    _set_access_cookie(resp, access_token)
    return resp


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> Response:
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    resp.delete_cookie("access_token")
    resp.delete_cookie("refresh_token")
    return resp
