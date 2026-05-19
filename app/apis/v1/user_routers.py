from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse, Response

from app.dependencies.security import get_request_user
from app.dtos.users import UserInfoResponse
from app.models.users import User
from app.services.users import UserManageService

user_router = APIRouter(prefix="/users", tags=["users"])


@user_router.get("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def user_me_info(
    user: Annotated[User, Depends(get_request_user)],
) -> ORJSONResponse:
    return ORJSONResponse(UserInfoResponse.model_validate(user).model_dump(), status_code=status.HTTP_200_OK)


@user_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_me(
    user: Annotated[User, Depends(get_request_user)],
    user_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    await user_service.withdraw(user.id)
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    resp.delete_cookie("refresh_token")
    return resp
