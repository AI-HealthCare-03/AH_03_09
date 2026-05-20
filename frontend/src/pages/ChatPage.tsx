import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import ChatSidebar from "../components/ChatSidebar";
import ChatWindow from "../components/ChatWindow";
import ChatInput from "../components/ChatInput";
import { getSessionDetail, streamMessage } from "../api/chat";
import { logout } from "../api/auth";
import type { ChatSession, ChatMessage } from "../types";

export default function ChatPage() {
  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [sending, setSending] = useState(false);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);
  const navigate = useNavigate();

  const loadSession = useCallback(async (session: ChatSession) => {
    setSelectedSession(session);
    setStreamingContent("");
    const res = await getSessionDetail(session.id);
    setMessages(res.data.messages);
  }, []);

  useEffect(() => {
    if (selectedSession) loadSession(selectedSession);
  }, [selectedSession?.id]);

  const handleSend = async (content: string) => {
    if (!selectedSession || sending) return;
    setSending(true);
    setStreamingContent("");

    const userMsg: ChatMessage = {
      id: Date.now(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    await streamMessage(
      selectedSession.id,
      content,
      (chunk) => setStreamingContent((prev) => prev + chunk),
      (messageId, title) => {
        const aiMsg: ChatMessage = {
          id: messageId,
          role: "assistant",
          content: streamingContent,
          created_at: new Date().toISOString(),
        };
        // re-load to get the full accurate content
        getSessionDetail(selectedSession.id).then((res) => {
          setMessages(res.data.messages);
          if (title) {
            setSelectedSession((prev) =>
              prev ? { ...prev, title } : prev
            );
            setSidebarRefresh((n) => n + 1);
          }
        });
        setStreamingContent("");
        setSending(false);
        void messageId;
        void aiMsg;
      },
      (detail) => {
        alert(`오류: ${detail}`);
        setStreamingContent("");
        setSending(false);
      }
    );
  };

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <div className="chat-layout">
      <ChatSidebar
        selectedId={selectedSession?.id ?? null}
        onSelect={loadSession}
        onNewSession={(s) => {
          setSelectedSession(s);
          setMessages([]);
        }}
        refreshKey={sidebarRefresh}
      />
      <main className="chat-main">
        <header className="chat-header">
          <h2>{selectedSession?.title ?? "AI 헬스케어 챗봇"}</h2>
          <button className="btn-logout" onClick={handleLogout}>
            로그아웃
          </button>
        </header>
        {selectedSession ? (
          <>
            <ChatWindow messages={messages} streamingContent={streamingContent} />
            <ChatInput onSend={handleSend} disabled={sending} />
          </>
        ) : (
          <div className="chat-placeholder">
            <p>왼쪽에서 채팅을 선택하거나 새 채팅을 시작하세요.</p>
          </div>
        )}
      </main>
    </div>
  );
}
