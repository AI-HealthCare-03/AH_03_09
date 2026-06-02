from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_profiles import HealthProfile, HealthProfileHistory, ProfileChangedBy


class HealthProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: int) -> HealthProfile | None:
        result = await self.session.execute(select(HealthProfile).where(HealthProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def create(self, user_id: int) -> HealthProfile:
        profile = HealthProfile(user_id=user_id)
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update_instance(self, profile: HealthProfile, data: dict) -> None:
        await self.session.execute(update(HealthProfile).where(HealthProfile.id == profile.id).values(**data))
        await self.session.commit()
        await self.session.refresh(profile)

    async def create_history(
        self,
        health_profile_id: int,
        snapshot: dict,
        changed_by: ProfileChangedBy,
    ) -> HealthProfileHistory:
        history = HealthProfileHistory(
            health_profile_id=health_profile_id,
            snapshot=snapshot,
            changed_by=changed_by,
        )
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(history)
        return history

    async def get_history(self, health_profile_id: int) -> list[HealthProfileHistory]:
        result = await self.session.execute(
            select(HealthProfileHistory)
            .where(HealthProfileHistory.health_profile_id == health_profile_id)
            .order_by(HealthProfileHistory.created_at.desc())
        )
        return list(result.scalars().all())
