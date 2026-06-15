from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.db.sqlalchemy_client import get_async_session
from app.dtos.health_profiles import HealthProfileUpdateRequest
from app.models.health_profiles import HealthProfile, HealthProfileHistory, ProfileChangedBy
from app.models.users import User
from app.repositories.health_profile_repository import HealthProfileRepository


def _map_kakao_gender(kakao_gender: str | None) -> str | None:
    if kakao_gender == "male":
        return "M"
    if kakao_gender == "female":
        return "F"
    return None


class HealthProfileService:
    def __init__(self, session: Annotated[AsyncSession, Depends(get_async_session)]) -> None:
        self.repo = HealthProfileRepository(session)

    async def get_or_create(self, user: User) -> HealthProfile:
        profile = await self.repo.get_by_user_id(user.id)
        if not profile:
            profile = await self.repo.create(
                user_id=user.id,
                gender=_map_kakao_gender(user.gender),
            )
        else:
            # 기존 프로필에 gender 미설정이면 카카오 데이터로 보완
            updates: dict = {}
            if profile.gender is None:
                mapped = _map_kakao_gender(user.gender)
                if mapped:
                    updates["gender"] = mapped
            if updates:
                await self.repo.update_instance(profile, updates)
                await self.repo.session.commit()
                await self.repo.session.refresh(profile)
        return profile

    async def update(self, user: User, data: HealthProfileUpdateRequest) -> HealthProfile:
        profile = await self.repo.get_by_user_id(user.id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="건강 프로필이 존재하지 않습니다.")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return profile

        snapshot = {
            "primary_conditions": profile.primary_conditions,
            "allergies": profile.allergies,
            "current_medications": profile.current_medications,
            "lifestyle_exercise": profile.lifestyle_exercise,
            "lifestyle_smoking": profile.lifestyle_smoking,
            "lifestyle_alcohol": profile.lifestyle_alcohol,
        }

        await self.repo.create_history(
            health_profile_id=profile.id,
            snapshot=snapshot,
            changed_by=ProfileChangedBy.USER,
        )
        await self.repo.update_instance(profile, update_data)
        await self.repo.session.commit()
        await self.repo.session.refresh(profile)
        return profile

    async def get_history(self, user: User) -> list[HealthProfileHistory]:
        profile = await self.repo.get_by_user_id(user.id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="건강 프로필이 존재하지 않습니다.")
        return await self.repo.get_history(profile.id)
