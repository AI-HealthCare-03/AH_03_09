from app.core.db.supabase_client import supabase


class ChatRepository:
    _conv_table = "conversations"
    _msg_table = "messages"

    def create_conversation(self, user_id: str, title: str = "새 대화") -> dict:
        res = supabase.table(self._conv_table).insert({"user_id": user_id, "title": title}).execute()
        return res.data[0]

    def get_conversations(self, user_id: str) -> list[dict]:
        res = (
            supabase.table(self._conv_table)
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return res.data

    def get_conversation(self, conversation_id: str, user_id: str) -> dict | None:
        res = (
            supabase.table(self._conv_table)
            .select("*")
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        return res.data

    def get_messages(self, conversation_id: str) -> list[dict]:
        res = (
            supabase.table(self._msg_table)
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .execute()
        )
        return res.data

    def create_message(self, conversation_id: str, role: str, content: str) -> dict:
        res = (
            supabase.table(self._msg_table)
            .insert({"conversation_id": conversation_id, "role": role, "content": content})
            .execute()
        )
        return res.data[0]

    def delete_conversation(self, conversation_id: str, user_id: str) -> None:
        supabase.table(self._conv_table).delete().eq("id", conversation_id).eq("user_id", user_id).execute()
