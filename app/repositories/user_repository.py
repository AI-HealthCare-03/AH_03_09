from app.core.db.supabase_client import supabase
from app.models.users import User


class UserRepository:
    _table = "users"

    def get_user(self, user_id: str) -> User | None:
        res = supabase.table(self._table).select("*").eq("id", user_id).maybe_single().execute()
        if res.data:
            return User(**res.data)
        return None

    def get_by_kakao_id(self, kakao_id: str) -> User | None:
        res = supabase.table(self._table).select("*").eq("kakao_id", kakao_id).maybe_single().execute()
        if res.data:
            return User(**res.data)
        return None

    def upsert_kakao_user(self, kakao_id: str, nickname: str, email: str | None, profile_image: str | None) -> User:
        data = {
            "kakao_id": kakao_id,
            "nickname": nickname,
            "email": email,
            "profile_image": profile_image,
        }
        res = (
            supabase.table(self._table)
            .upsert(data, on_conflict="kakao_id")
            .execute()
        )
        return User(**res.data[0])
