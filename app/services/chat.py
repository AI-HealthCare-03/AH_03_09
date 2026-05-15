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

DANGER_KEYWORDS = [
    "자살", "자해", "독약", "극약", "과다복용",
    "수면제 다량", "농약 먹으면", "죽고 싶어", "목숨 끊",
]

MEDICAL_OVERREACH = [
    "진단해드리겠습니다", "처방해드리겠습니다",
    "치료해드릴게요", "이 약을 드세요", "확실히 이 병입니다",
]

MAX_RETRY = 3
MIN_RESPONSE_LENGTH = 20

EMERGENCY_RESPONSE = (
    "⚠️ 응급 상황이 의심됩니다. "
    "즉시 119에 전화하거나 가까운 응급실을 방문해 주세요. "
    "전문 의료진의 도움을 받으시기 바랍니다."
)

SAFE_FALLBACK = (
    "죄송합니다. 현재 적절한 의료 정보를 제공하기 어렵습니다. "
    "증상이 심각하거나 지속된다면 반드시 전문의를 방문하시거나 "
    "응급 상황 시 119에 연락하세요."
)

_openai = OpenAI(api_key=config.OPENAI_API_KEY)


def _is_safe_input(content: str) -> bool:
    return not any(kw in content for kw in DANGER_KEYWORDS)


def _is_quality_ok(text: str) -> bool:
    if len(text.strip()) < MIN_RESPONSE_LENGTH:
        return False
    if any(kw in text for kw in MEDICAL_OVERREACH):
        return False
    return True


def _build_messages(history: list[dict], attempt: int) -> list[dict]:
    base = SYSTEM_PROMPT
    if attempt == 1:
        base += (
            " 절대로 진단, 처방, 치료를 직접 제공하지 마세요. "
            "반드시 '전문의 상담을 권고합니다'로 마무리하세요."
        )
    elif attempt >= 2:
        base += (
            " 진단이나 처방 없이 일반적인 의료 정보만 안내하세요. "
            "구체적인 약 이름이나 치료법을 직접 지시하지 마세요. "
            "모든 답변 마지막에 전문의 상담을 권고하세요."
        )
    messages = [{"role": "system", "content": base}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history[-10:]]
    return messages


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

        # [1] 위험 키워드 입력 안전성 검사
        if not _is_safe_input(content):
            assistant_msg = self.repo.create_message(
                conversation_id=conversation_id,
                role="assistant",
                content=EMERGENCY_RESPONSE,
            )
            return assistant_msg

        # [2] 사용자 메시지 저장
        self.repo.create_message(conversation_id=conversation_id, role="user", content=content)

        # [3] 히스토리 조회
        history = self.repo.get_messages(conversation_id=conversation_id)

        # [4] E-O 자가최적화 루프 (최대 MAX_RETRY회 재시도)
        assistant_content = SAFE_FALLBACK
        for attempt in range(MAX_RETRY):
            messages = _build_messages(history, attempt)
            completion = _openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            text = completion.choices[0].message.content or ""

            if _is_quality_ok(text):
                assistant_content = text
                break

        # [5] 최종 응답 저장 및 반환
        assistant_msg = self.repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
        )
        return assistant_msg
