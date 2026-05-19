from fastapi import HTTPException
from starlette import status
from tortoise.transactions import in_transaction

from app.dtos.health_profiles import HealthProfileUpdateRequest
from app.models.health_profiles import HealthProfile, HealthProfileHistory, ProfileChangedBy
from app.models.users import User
from app.repositories.health_profile_repository import HealthProfileRepository


class HealthProfileService:
    def __init__(self):
        self.repo = HealthProfileRepository()

    async def get_or_create(self, user: User) -> HealthProfile:
        profile = await self.repo.get_by_user_id(user.id)
        if not profile:
            async with in_transaction():
                profile = await self.repo.create(user_id=user.id)
        return profile

    async def update(self, user: User, data: HealthProfileUpdateRequest) -> HealthProfile:
        profile = await self.repo.get_by_user_id(user.id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="건강 프로필이 존재하지 않습니다.")

        update_data = data.model_dump(exclude_none=True)
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

        async with in_transaction():
            await self.repo.create_history(
                health_profile_id=profile.id,
                snapshot=snapshot,
                changed_by=ProfileChangedBy.USER,
            )
            await self.repo.update_instance(profile, update_data)
            await profile.refresh_from_db()

        return profile

    async def get_history(self, user: User) -> list[HealthProfileHistory]:
        profile = await self.repo.get_by_user_id(user.id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="건강 프로필이 존재하지 않습니다.")
        return await self.repo.get_history(profile.id)
