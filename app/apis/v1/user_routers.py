from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.dependencies.security import get_request_user
from app.dtos.users import UserInfoResponse, WithdrawRequest
from app.models.users import User
from app.services.users import UserManageService

user_router = APIRouter(prefix="/users", tags=["users"])

WITHDRAW_CONFIRMATION_TEXT = "회원탈퇴합니다"


@user_router.get("/me", status_code=status.HTTP_200_OK)
async def user_me_info(
    user: Annotated[User, Depends(get_request_user)],
) -> UserInfoResponse:
    return UserInfoResponse.model_validate(user)


@user_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_me(
    body: WithdrawRequest,
    user: Annotated[User, Depends(get_request_user)],
    user_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    if body.confirmation_text != WITHDRAW_CONFIRMATION_TEXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="확인 문구가 일치하지 않습니다.",
        )
    await user_service.withdraw(user.id)
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    resp.delete_cookie("refresh_token")
    return resp
