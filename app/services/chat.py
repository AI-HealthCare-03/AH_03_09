from fastapi import HTTPException
from openai import OpenAI
from starlette import status

from app.core import config
from app.repositories.chat_repository import ChatRepository

SYSTEM_PROMPT = (
    "당신은 의료 정보 안내 챗봇입니다. "
    "증상, 약품, 병원 관련 정보를 친절하게 안내합니다. "
    "의료적 진단은 제공하지 않으며, 심각한 증상이 있을 경우 반드시 전문의 상담을 권고합니다. "
    "답변은 한국어로 제공합니다."
)

_openai = OpenAI(api_key=config.OPENAI_API_KEY)


class ChatService:
    def __init__(self) -> None:
        self.repo = ChatRepository()

    def create_conversation(self, user_id: str, title: str = "새 대화") -> dict:
        return self.repo.create_conversation(user_id=user_id, title=title)

    def get_conversations(self, user_id: str) -> list[dict]:
        return self.repo.get_conversations(user_id=user_id)

    def get_conversation_with_messages(self, conversation_id: str, user_id: str) -> dict:
        conv = self.repo.get_conversation(conversation_id=conversation_id, user_id=user_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대화를 찾을 수 없습니다.")
        messages = self.repo.get_messages(conversation_id=conversation_id)
        return {**conv, "messages": messages}

    def delete_conversation(self, conversation_id: str, user_id: str) -> None:
        conv = self.repo.get_conversation(conversation_id=conversation_id, user_id=user_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대화를 찾을 수 없습니다.")
        self.repo.delete_conversation(conversation_id=conversation_id, user_id=user_id)

    def send_message(self, conversation_id: str, user_id: str, content: str) -> dict:
        conv = self.repo.get_conversation(conversation_id=conversation_id, user_id=user_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="대화를 찾을 수 없습니다.")

        self.repo.create_message(conversation_id=conversation_id, role="user", content=content)

        history = self.repo.get_messages(conversation_id=conversation_id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += [{"role": m["role"], "content": m["content"]} for m in history[-10:]]

        completion = _openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        assistant_content = completion.choices[0].message.content or ""

        assistant_msg = self.repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
        )
        return assistant_msg
