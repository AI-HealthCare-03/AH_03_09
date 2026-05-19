from app.models.health_profiles import HealthProfile, HealthProfileHistory, ProfileChangedBy


class HealthProfileRepository:
    def __init__(self):
        self._model = HealthProfile
        self._history_model = HealthProfileHistory

    async def get_by_user_id(self, user_id: int) -> HealthProfile | None:
        return await self._model.get_or_none(user_id=user_id)

    async def create(self, user_id: int) -> HealthProfile:
        return await self._model.create(user_id=user_id)

    async def update_instance(self, profile: HealthProfile, data: dict) -> None:
        for key, value in data.items():
            setattr(profile, key, value)
        await profile.save(update_fields=list(data.keys()) + ["updated_at"])

    async def create_history(
        self,
        health_profile_id: int,
        snapshot: dict,
        changed_by: ProfileChangedBy,
    ) -> HealthProfileHistory:
        return await self._history_model.create(
            health_profile_id=health_profile_id,
            snapshot=snapshot,
            changed_by=changed_by,
        )

    async def get_history(self, health_profile_id: int) -> list[HealthProfileHistory]:
        return await self._history_model.filter(
            health_profile_id=health_profile_id
        ).order_by("-created_at")
