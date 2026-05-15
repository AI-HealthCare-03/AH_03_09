import httpx
from fastapi import HTTPException
from starlette import status

from app.core import config
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService
from app.core.jwt.tokens import AccessToken, RefreshToken

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_URL = "https://kapi.kakao.com/v2/user/me"


class AuthService:
    def __init__(self) -> None:
        self.user_repo = UserRepository()
        self.jwt_service = JwtService()

    def get_kakao_auth_url(self) -> str:
        return (
            f"https://kauth.kakao.com/oauth/authorize"
            f"?client_id={config.KAKAO_CLIENT_ID}"
            f"&redirect_uri={config.KAKAO_REDIRECT_URI}"
            f"&response_type=code"
        )

    async def exchange_kakao_code(self, code: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                KAKAO_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": config.KAKAO_CLIENT_ID,
                    "client_secret": config.KAKAO_CLIENT_SECRET,
                    "redirect_uri": config.KAKAO_REDIRECT_URI,
                    "code": code,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 토큰 발급 실패")
        return resp.json()["access_token"]

    async def get_kakao_user_info(self, kakao_access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                KAKAO_USER_URL,
                headers={"Authorization": f"Bearer {kakao_access_token}"},
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 사용자 정보 조회 실패")
        return resp.json()

    async def kakao_login(self, code: str) -> dict[str, AccessToken | RefreshToken]:
        kakao_token = await self.exchange_kakao_code(code)
        kakao_info = await self.get_kakao_user_info(kakao_token)

        kakao_id = str(kakao_info["id"])
        kakao_account = kakao_info.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        nickname = profile.get("nickname", "사용자")
        email = kakao_account.get("email")
        profile_image = profile.get("profile_image_url")

        user = self.user_repo.upsert_kakao_user(
            kakao_id=kakao_id,
            nickname=nickname,
            email=email,
            profile_image=profile_image,
        )
        return self.jwt_service.issue_jwt_pair(user)
