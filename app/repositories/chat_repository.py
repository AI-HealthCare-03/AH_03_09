from pgvector.psycopg import register_vector

from app.core.db.postgres_client import get_pool


class ChatRepository:
    def create_conversation(self, user_id: str, title: str = "새 대화") -> dict:
        with get_pool().connection() as conn:
            return conn.execute(
                "INSERT INTO conversations (user_id, title) VALUES (%s, %s) RETURNING *",
                (user_id, title),
            ).fetchone()

    def get_conversations(self, user_id: str) -> list[dict]:
        with get_pool().connection() as conn:
            return conn.execute(
                "SELECT * FROM conversations WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()

    def get_conversation(self, conversation_id: str, user_id: str) -> dict | None:
        with get_pool().connection() as conn:
            return conn.execute(
                "SELECT * FROM conversations WHERE id = %s AND user_id = %s",
                (conversation_id, user_id),
            ).fetchone()

    def get_messages(self, conversation_id: str) -> list[dict]:
        with get_pool().connection() as conn:
            return conn.execute(
                "SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
                (conversation_id,),
            ).fetchall()

    def create_message(
        self, conversation_id: str, role: str, content: str, embedding=None
    ) -> dict:
        with get_pool().connection() as conn:
            register_vector(conn)
            return conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, embedding)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (conversation_id, role, content, embedding),
            ).fetchone()

    def search_similar_messages(self, embedding, limit: int = 5) -> list[dict]:
        """PGvector 코사인 유사도 기반 유사 메시지 검색"""
        with get_pool().connection() as conn:
            register_vector(conn)
            return conn.execute(
                """
                SELECT *, (embedding <=> %s) AS distance
                FROM messages
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (embedding, embedding, limit),
            ).fetchall()

    def delete_conversation(self, conversation_id: str, user_id: str) -> None:
        with get_pool().connection() as conn:
            conn.execute(
                "DELETE FROM conversations WHERE id = %s AND user_id = %s",
                (conversation_id, user_id),
            )
