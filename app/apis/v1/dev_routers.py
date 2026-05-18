"""개발/테스트용 라우터. Swagger UI에서 Kakao 로그인과 채팅을 가짜 데이터로 검증한다.

외부 의존(Kakao OAuth, Redis, AI worker, DB)을 모두 우회하며 메모리 안에 상태를 보관한다.
운영 환경(ENV=prod)에서는 라우터 자체가 마운트되지 않는다.
"""
from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.models.users import User
from app.services.jwt import JwtService

dev_router = APIRouter(prefix="/dev", tags=["dev (fake data)"])

_bearer = HTTPBearer(description="가짜 로그인으로 발급받은 access_token을 입력하세요.")


# ---------- 인메모리 저장소 ----------

_FAKE_USERS: dict[str, User] = {}
_FAKE_SESSIONS: dict[UUID, dict] = {}  # session_id -> {user_id, title, created_at, updated_at}
_FAKE_MESSAGES: dict[UUID, list[dict]] = {}  # session_id -> list of message dicts
_message_seq = 0


def _next_message_id() -> int:
    global _message_seq
    _message_seq += 1
    return _message_seq


def _get_current_user(
    credential: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> User:
    """dev 토큰을 검증하고 인메모리 사용자 객체를 반환한다."""
    token = credential.credentials
    verified = JwtService().verify_jwt(token=token, token_type="access")
    user_id = verified.payload.get("user_id")
    user = _FAKE_USERS.get(str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="dev 사용자를 찾을 수 없습니다. /dev/login 으로 먼저 로그인하세요.",
        )
    return user


# ---------- 스키마 ----------

class DevLoginRequest(BaseModel):
    user_id: str = Field(default="1", description="가짜 사용자 ID")
    kakao_id: str = Field(default="fake-kakao-12345", description="가짜 Kakao ID")
    nickname: str = Field(default="테스트 사용자", description="표시 이름")
    email: str | None = Field(default="test@example.com", description="이메일")
    profile_image: str | None = Field(default=None, description="프로필 이미지 URL")


class DevLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: User


class DevSessionCreateRequest(BaseModel):
    title: str = "새 대화"


class DevSessionResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class DevMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="유저가 보낼 메시지")


class DevMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class DevSendMessageResponse(BaseModel):
    user_message: DevMessageResponse
    assistant_message: DevMessageResponse


class DevMessageListResponse(BaseModel):
    messages: list[DevMessageResponse]


# ---------- 인증 ----------

@dev_router.post(
    "/login",
    response_model=DevLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="가짜 Kakao 로그인",
    description="외부 Kakao API 호출 없이 인메모리 사용자를 생성하고 JWT 토큰을 발급합니다. "
                "응답의 access_token을 복사해 우측 상단 'Authorize' 버튼에 붙여 넣으면 "
                "이후 dev 채팅 API를 호출할 수 있습니다.",
)
def dev_login(body: DevLoginRequest) -> DevLoginResponse:
    user = User(
        id=body.user_id,
        kakao_id=body.kakao_id,
        nickname=body.nickname,
        email=body.email,
        profile_image=body.profile_image,
        created_at=datetime.now(),
    )
    _FAKE_USERS[user.id] = user

    tokens = JwtService().issue_jwt_pair(user)
    return DevLoginResponse(
        access_token=str(tokens["access_token"]),
        refresh_token=str(tokens["refresh_token"]),
        user=user,
    )


@dev_router.get(
    "/me",
    response_model=User,
    summary="현재 로그인한 가짜 사용자 조회",
)
def dev_me(user: Annotated[User, Depends(_get_current_user)]) -> User:
    return user


# ---------- 채팅 세션 ----------

@dev_router.post(
    "/chat/sessions",
    response_model=DevSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="가짜 채팅 세션 생성",
)
def dev_create_session(
    body: DevSessionCreateRequest,
    user: Annotated[User, Depends(_get_current_user)],
) -> DevSessionResponse:
    now = datetime.now()
    session_id = uuid4()
    _FAKE_SESSIONS[session_id] = {
        "user_id": user.id,
        "title": body.title,
        "created_at": now,
        "updated_at": now,
    }
    _FAKE_MESSAGES[session_id] = []
    return DevSessionResponse(
        id=session_id,
        title=body.title,
        created_at=now,
        updated_at=now,
    )


@dev_router.get(
    "/chat/sessions",
    response_model=list[DevSessionResponse],
    summary="가짜 채팅 세션 목록",
)
def dev_list_sessions(
    user: Annotated[User, Depends(_get_current_user)],
) -> list[DevSessionResponse]:
    items = [
        DevSessionResponse(id=sid, title=s["title"], created_at=s["created_at"], updated_at=s["updated_at"])
        for sid, s in _FAKE_SESSIONS.items()
        if s["user_id"] == user.id
    ]
    items.sort(key=lambda x: x.updated_at, reverse=True)
    return items


# ---------- 채팅 메시지 ----------

def _generate_fake_reply(user_text: str) -> str:
    """간단한 규칙 기반 가짜 AI 응답."""
    lower = user_text.strip().lower()
    if any(k in lower for k in ("안녕", "hi", "hello", "반가워")):
        return "안녕하세요! 무엇을 도와드릴까요? 증상이나 약 이름을 알려 주시면 정보를 안내해 드릴게요."
    if any(k in lower for k in ("두통", "headache", "머리")):
        return "두통은 수분 부족, 수면 부족, 스트레스 등이 원인일 수 있어요. 증상이 24시간 이상 지속되면 진료를 권장드립니다. (※ 본 응답은 데모용 가짜 데이터입니다.)"
    if any(k in lower for k in ("약", "복용", "처방", "medic")):
        return f"'{user_text}' 관련 정보를 찾고 있어요. (※ 본 응답은 데모용 가짜 데이터이며 실제 의료 자문이 아닙니다.)"
    return f"[가짜 AI 응답] 당신의 메시지: \"{user_text}\" — 실제 모델은 Redis/AI worker가 연결되면 동작합니다."


@dev_router.post(
    "/chat/sessions/{session_id}/messages",
    response_model=DevSendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="메시지 전송 (WebSocket 대신 동기 REST)",
    description="유저 메시지를 저장하고 즉시 가짜 AI 응답을 함께 반환합니다. "
                "WebSocket·Redis·AI worker 없이 Swagger UI에서 채팅 흐름을 검증할 수 있습니다.",
)
def dev_send_message(
    session_id: UUID,
    body: DevMessageRequest,
    user: Annotated[User, Depends(_get_current_user)],
) -> DevSendMessageResponse:
    session = _FAKE_SESSIONS.get(session_id)
    if not session or session["user_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")

    now = datetime.now()
    user_msg = {
        "id": _next_message_id(),
        "role": "user",
        "content": body.content,
        "created_at": now,
    }
    assistant_msg = {
        "id": _next_message_id(),
        "role": "assistant",
        "content": _generate_fake_reply(body.content),
        "created_at": datetime.now(),
    }
    _FAKE_MESSAGES[session_id].extend([user_msg, assistant_msg])
    session["updated_at"] = assistant_msg["created_at"]

    return DevSendMessageResponse(
        user_message=DevMessageResponse(**user_msg),
        assistant_message=DevMessageResponse(**assistant_msg),
    )


@dev_router.get(
    "/chat/sessions/{session_id}/messages",
    response_model=DevMessageListResponse,
    summary="가짜 채팅 메시지 이력",
)
def dev_list_messages(
    session_id: UUID,
    user: Annotated[User, Depends(_get_current_user)],
) -> DevMessageListResponse:
    session = _FAKE_SESSIONS.get(session_id)
    if not session or session["user_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")
    msgs = _FAKE_MESSAGES.get(session_id, [])
    return DevMessageListResponse(messages=[DevMessageResponse(**m) for m in msgs])
