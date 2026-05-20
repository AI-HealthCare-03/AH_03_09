import api from "./client";
import type { ChatSession, ChatSessionDetail } from "../types";

export const getSessions = () => api.get<ChatSession[]>("/chat/sessions");

export const createSession = (title: string) =>
  api.post<ChatSession>("/chat/sessions", { title });

export const getSessionDetail = (sessionId: number) =>
  api.get<ChatSessionDetail>(`/chat/sessions/${sessionId}`);

export const deleteSession = (sessionId: number) =>
  api.delete(`/chat/sessions/${sessionId}`);

export const streamMessage = async (
  sessionId: number,
  content: string,
  onChunk: (chunk: string) => void,
  onDone: (messageId: number, title: string | null) => void,
  onError: (detail: string) => void
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

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE messages are separated by \n\n
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
          onDone(parsed.message_id, parsed.title ?? null);
          return;
        } else if (parsed.chunk !== undefined) {
          onChunk(parsed.chunk);
        }
      } catch {
        // ignore malformed lines
      }
    }
  }
};
