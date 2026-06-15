from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse as Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.sqlalchemy_client import get_async_session
from app.dependencies.security import get_request_user
from app.dtos.health_profiles import HealthProfileHistoryResponse, HealthProfileResponse, HealthProfileUpdateRequest
from app.models.users import User
from app.services.health_profiles import HealthProfileService

health_profile_router = APIRouter(prefix="/health-profile", tags=["health-profile"])


@health_profile_router.get("", response_model=HealthProfileResponse, status_code=status.HTTP_200_OK)
async def get_health_profile(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HealthProfileService, Depends(HealthProfileService)],
) -> Response:
    result = await service.get_or_create(user)
    return Response(HealthProfileResponse.model_validate(result).model_dump(mode="json"))


@health_profile_router.patch("", response_model=HealthProfileResponse, status_code=status.HTTP_200_OK)
async def update_health_profile(
    body: HealthProfileUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HealthProfileService, Depends(HealthProfileService)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Response:
    await service.get_or_create(user)  # 신규 유저는 프로필이 없으므로 먼저 생성
    result = await service.update(user, body)
    # 챗봇이 users 테이블에서 gender/age_range를 읽으므로 동기화
    if body.gender is not None:
        user.gender = body.gender.value if hasattr(body.gender, "value") else body.gender
    if body.age_range is not None:
        user.age_range = body.age_range
    await session.commit()
    return Response(HealthProfileResponse.model_validate(result).model_dump(mode="json"))


@health_profile_router.get(
    "/history", response_model=list[HealthProfileHistoryResponse], status_code=status.HTTP_200_OK
)
async def get_health_profile_history(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HealthProfileService, Depends(HealthProfileService)],
) -> Response:
    result = await service.get_history(user)
    return Response([HealthProfileHistoryResponse.model_validate(h).model_dump(mode="json") for h in result])
