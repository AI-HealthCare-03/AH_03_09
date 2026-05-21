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
