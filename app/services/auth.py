import httpx
from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from starlette import status
from tortoise.transactions import in_transaction

from app.core import config
from app.core.jwt.tokens import AccessToken, RefreshToken
from app.core.utils.common import normalize_phone_number
from app.core.utils.security import hash_password, verify_password
from app.dtos.auth import LoginRequest, SignUpRequest
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_URL = "https://kapi.kakao.com/v2/user/me"


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.jwt_service = JwtService()

    async def signup(self, data: SignUpRequest) -> User:
        # 이메일 중복 체크
        await self.check_email_exists(data.email)

        # 입력받은 휴대폰 번호를 노말라이즈
        normalized_phone_number = normalize_phone_number(data.phone_number)

        # 휴대폰 번호 중복 체크
        await self.check_phone_number_exists(normalized_phone_number)

        # 유저 생성
        async with in_transaction():
            user = await self.user_repo.create_user(
                email=data.email,
                hashed_password=hash_password(data.password),  # 해시화된 비밀번호를 사용
                name=data.name,
                phone_number=normalized_phone_number,
                gender=data.gender,
                birthday=data.birth_date,
            )

            return user

    async def authenticate(self, data: LoginRequest) -> User:
        # 이메일로 사용자 조회
        email = str(data.email)
        user = await self.user_repo.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 또는 비밀번호가 올바르지 않습니다."
            )

        # 비밀번호 검증
        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 또는 비밀번호가 올바르지 않습니다."
            )

        # 활성 사용자 체크
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="비활성화된 계정입니다.")

        return user

    async def login(self, user: User) -> dict[str, AccessToken | RefreshToken]:
        await self.user_repo.update_last_login(user.id)
        return self.jwt_service.issue_jwt_pair(user)

    async def check_email_exists(self, email: str | EmailStr) -> None:
        if await self.user_repo.exists_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 이메일입니다.")

    async def check_phone_number_exists(self, phone_number: str) -> None:
        if await self.user_repo.exists_by_phone_number(phone_number):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 휴대폰 번호입니다.")

    async def kakao_callback(self, code: str) -> dict[str, AccessToken | RefreshToken]:
        async with httpx.AsyncClient() as client:
            # 1. 인가 코드 → 카카오 액세스 토큰 교환
            token_res = await client.post(
                KAKAO_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": config.KAKAO_REST_API_KEY,
                    "redirect_uri": config.KAKAO_REDIRECT_URI,
                    "code": code,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if token_res.status_code != 200:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 토큰 발급 실패")
            kakao_access_token = token_res.json()["access_token"]

            # 2. 카카오 사용자 정보 조회
            user_res = await client.get(
                KAKAO_USER_URL,
                headers={"Authorization": f"Bearer {kakao_access_token}"},
            )
            if user_res.status_code != 200:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 사용자 정보 조회 실패")
            kakao_data = user_res.json()

        kakao_id = str(kakao_data["id"])
        kakao_account = kakao_data.get("kakao_account", {})
        email = kakao_account.get("email", f"{kakao_id}@kakao.local")
        name = kakao_account.get("profile", {}).get("nickname", "카카오사용자")

        # 3. kakao_id로 기존 유저 조회 → 없으면 이메일로 조회 → 없으면 신규 생성
        user = await self.user_repo.get_by_kakao_id(kakao_id)
        if not user:
            existing = await self.user_repo.get_user_by_email(email)
            if existing:
                await self.user_repo.update_kakao_id(existing, kakao_id)
                user = existing
            else:
                async with in_transaction():
                    user = await self.user_repo.create_kakao_user(
                        kakao_id=kakao_id,
                        email=email,
                        name=name,
                    )

        return await self.login(user)
