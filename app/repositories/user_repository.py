from app.core.db.postgres_client import get_pool
from app.models.users import User


class UserRepository:
    def get_user(self, user_id: str) -> User | None:
        with get_pool().connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = %s", (user_id,)
            ).fetchone()
        return User(**row) if row else None

    def get_by_kakao_id(self, kakao_id: str) -> User | None:
        with get_pool().connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE kakao_id = %s", (kakao_id,)
            ).fetchone()
        return User(**row) if row else None

    def upsert_kakao_user(
        self, kakao_id: str, nickname: str, email: str | None, profile_image: str | None
    ) -> User:
        with get_pool().connection() as conn:
            row = conn.execute(
                """
                INSERT INTO users (kakao_id, nickname, email, profile_image)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (kakao_id)
                DO UPDATE SET nickname = EXCLUDED.nickname,
                              email = EXCLUDED.email,
                              profile_image = EXCLUDED.profile_image
                RETURNING *
                """,
                (kakao_id, nickname, email, profile_image),
            ).fetchone()
        return User(**row)
