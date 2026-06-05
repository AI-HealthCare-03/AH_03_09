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
  guideId: string | null | undefined,
  onChunk: (chunk: string) => void,
  onDone: (messageId: number, title: string | null) => void,
  onError: (detail: string) => void,
  onDelay?: (detail: string) => void,
): Promise<void> => {
  const res = await fetch(`/api/v1/chat/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify({ content, guide_id: guideId ?? null }),
  });

  if (!res.ok || !res.body) {
    onError("서버 연결에 실패했습니다.");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let streamCompleted = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const data = JSON.parse(line);
        if (data.type === "chunk") {
          onChunk(data.chunk);
        } else if (data.type === "done") {
          streamCompleted = true;
          onDone(0, null);
          return;
        } else if (data.type === "error") {
          onError(data.detail ?? "알 수 없는 오류가 발생했습니다.");
          return;
        } else if (data.type === "delay") {
          onDelay?.(data.detail);
        }
      } catch {
        // ignore malformed lines
      }
    }
  }

  if (!streamCompleted) {
    onError("연결이 끊어졌습니다. 다시 시도해주세요.");
  }
};
