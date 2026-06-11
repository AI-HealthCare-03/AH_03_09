from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.guides import (
    FeedbackRequest,
    FeedbackResponse,
    FeedbackStatusResponse,
    GenerateGuideRequest,
    GenerateGuideResponse,
    GuideContextResponse,
    GuideListResponse,
    GuideResponse,
    GuideStatusResponse,
    UpdateFeedbackStatusRequest,
)
from app.models.users import User
from app.services.guides import GuideService

guide_router = APIRouter(prefix="/guides", tags=["LLM 가이드"])

_AUTH = Annotated[User, Depends(get_request_user)]


@guide_router.get(
    "",
    response_model=GuideListResponse,
    status_code=status.HTTP_200_OK,
    summary="내 가이드 목록 조회",
)
async def list_guides(
    current_user: _AUTH,
    guide_service: Annotated[GuideService, Depends(GuideService)],
) -> Response:
    result = await guide_service.list_guides(str(current_user.id))
    return Response(content=result.model_dump(), status_code=status.HTTP_200_OK)


@guide_router.post(
    "/generate",
    response_model=GenerateGuideResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="가이드 생성 요청 (REQ-LLM-001)",
)
async def generate_guide(
    request: GenerateGuideRequest,
    guide_service: Annotated[GuideService, Depends(GuideService)],
) -> Response:
    result = await guide_service.create_guide_job(request)
    return Response(content=result.model_dump(), status_code=status.HTTP_202_ACCEPTED)


# /status/{job_id}는 반드시 /{guide_id} 보다 먼저 등록해야 라우팅 충돌 방지
@guide_router.get(
    "/status/{job_id}",
    response_model=GuideStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="가이드 생성 상태 조회 (REQ-LLM-003)",
)
async def get_guide_status(
    job_id: str,
    guide_service: Annotated[GuideService, Depends(GuideService)],
) -> Response:
    result = await guide_service.get_job_status(job_id)
    return Response(content=result.model_dump(), status_code=status.HTTP_200_OK)


@guide_router.get(
    "/{guide_id}",
    response_model=GuideResponse,
    status_code=status.HTTP_200_OK,
    summary="가이드 결과 조회 (REQ-LLM-008)",
)
async def get_guide(
    guide_id: str,
    guide_service: Annotated[GuideService, Depends(GuideService)],
) -> Response:
    result = await guide_service.get_guide(guide_id)
    return Response(content=result.model_dump(), status_code=status.HTTP_200_OK)


@guide_router.post(
    "/{guide_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="피드백 제출 (REQ-LLM-009)",
)
async def submit_feedback(
    guide_id: str,
    request: FeedbackRequest,
    guide_service: Annotated[GuideService, Depends(GuideService)],
) -> Response:
    result = await guide_service.submit_feedback(guide_id, request)
    return Response(content=result.model_dump(), status_code=status.HTTP_201_CREATED)


@guide_router.get(
    "/{guide_id}/feedback/status",
    response_model=FeedbackStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="피드백 제출 상태 조회 (REQ-LLM-010)",
)
async def get_feedback_status(
    guide_id: str,
    guide_service: Annotated[GuideService, Depends(GuideService)],
) -> Response:
    result = await guide_service.get_feedback_status(guide_id)
    return Response(content=result.model_dump(), status_code=status.HTTP_200_OK)


@guide_router.patch(
    "/{guide_id}/feedback/status",
    response_model=FeedbackStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="피드백 제출 상태 업데이트 (REQ-LLM-010)",
)
async def update_feedback_status(
    guide_id: str,
    request: UpdateFeedbackStatusRequest,
    guide_service: Annotated[GuideService, Depends(GuideService)],
) -> Response:
    result = await guide_service.update_feedback_status(guide_id, request)
    return Response(content=result.model_dump(), status_code=status.HTTP_200_OK)


@guide_router.get(
    "/{guide_id}/context",
    response_model=GuideContextResponse,
    status_code=status.HTTP_200_OK,
    summary="챗봇 연동용 가이드 컨텍스트 조회 (REQ-LLM-011)",
)
async def get_guide_context(
    guide_id: str,
    guide_service: Annotated[GuideService, Depends(GuideService)],
) -> Response:
    result = await guide_service.get_guide_context(guide_id)
    return Response(content=result.model_dump(), status_code=status.HTTP_200_OK)
