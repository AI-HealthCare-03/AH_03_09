import { request } from "@/lib/api";
import type {
  ChatMessageListResponse,
  ChatSessionResponse,
  SendMessageResponse,
} from "@/types/api";

export function fetchSessions(): Promise<ChatSessionResponse[]> {
  return request<ChatSessionResponse[]>("/chat/sessions");
}

export function createSession(title?: string): Promise<ChatSessionResponse> {
  return request<ChatSessionResponse>("/chat/sessions", {
    method: "POST",
    body: JSON.stringify({ title: title ?? "새 대화" }),
  });
}

export function fetchMessages(sessionId: string): Promise<ChatMessageListResponse> {
  return request<ChatMessageListResponse>(`/chat/sessions/${sessionId}/messages`);
}

export function sendMessage(sessionId: string, content: string): Promise<SendMessageResponse> {
  return request<SendMessageResponse>(`/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function deleteSession(sessionId: string): Promise<void> {
  return request<void>(`/chat/sessions/${sessionId}`, { method: "DELETE" });
}

export function submitFeedback(
  sessionId: string,
  messageId: number,
  feedback: "good" | "bad",
): Promise<void> {
  return request<void>(`/chat/sessions/${sessionId}/messages/${messageId}/feedback`, {
    method: "PATCH",
    body: JSON.stringify({ feedback }),
  });
}

export const streamMessage = async (
  sessionId: string,
  content: string,
  onChunk: (chunk: string) => void,
  onDone: (messageId: number, title: string | null) => void,
  onError: (detail: string) => void,
): Promise<void> => {
  const res = await fetch(`/api/v1/chat/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ content }),
  });

  if (!res.ok || !res.body) {
    onError("서버 연결에 실패했습니다.");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";
  let streamCompleted = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const messages = buffer.split("\n\n");
    buffer = messages.pop() ?? "";

    for (const message of messages) {
      const lines = message.split("\n");
      currentEvent = "";
      let dataLine = "";

      for (const line of lines) {
        if (line.startsWith("event:")) currentEvent = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLine = line.slice(5).trim();
      }

      if (!dataLine) continue;

      try {
        const parsed = JSON.parse(dataLine);
        if (currentEvent === "error") {
          onError(parsed.detail ?? "알 수 없는 오류가 발생했습니다.");
          return;
        } else if (currentEvent === "done") {
          streamCompleted = true;
          onDone(parsed.message_id, parsed.title ?? null);
          return;
        } else if (parsed.chunk !== undefined) {
          onChunk(parsed.chunk);
        }
      } catch {
        // ignore malformed SSE lines
      }
    }
  }

  if (!streamCompleted) {
    onError("연결이 끊어졌습니다. 다시 시도해주세요.");
  }
};
