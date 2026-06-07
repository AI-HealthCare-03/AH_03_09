import { useState, useEffect, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import ChatSidebar from "../components/ChatSidebar";
import ChatWindow from "../components/ChatWindow";
import ChatInput from "../components/ChatInput";
import { fetchMessages, streamMessage } from "../api/chat";
import { logout } from "../api/auth";
import { useAuthStore } from "@/store/authStore";
import type { ChatSessionResponse, ChatMessageResponse } from "@/types/api";

const EMERGENCY_KEYWORDS = ["응급", "119", "심정지", "의식 없", "숨 못 쉬"];

export default function ChatPage() {
  const [selectedSession, setSelectedSession] = useState<ChatSessionResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessageResponse[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [sending, setSending] = useState(false);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [hasEmergency, setHasEmergency] = useState(false);
  const navigate = useNavigate();

  const loadSession = useCallback(async (session: ChatSessionResponse) => {
    setSelectedSession(session);
    setStreamingContent("");
    setError(null);
    const res = await fetchMessages(session.id);
    setMessages(res.messages);
  }, []);

  useEffect(() => {
    if (selectedSession) loadSession(selectedSession);
  }, [selectedSession?.id, loadSession]);

  const handleSend = async (content: string) => {
    if (!selectedSession || sending) return;

    const isEmergency = EMERGENCY_KEYWORDS.some(kw => content.includes(kw));
    setHasEmergency(isEmergency);

    setSending(true);
    setStreamingContent("");
    setError(null);

    const userMsg: ChatMessageResponse = {
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
      (_messageId, title) => {
        fetchMessages(selectedSession.id).then((res) => {
          setMessages(res.messages);
          if (title) {
            setSelectedSession((prev) => prev ? { ...prev, title } : prev);
            setSidebarRefresh((n) => n + 1);
          }
        });
        setStreamingContent("");
        setSending(false);
      },
      (detail) => {
        setError(detail);
        setStreamingContent("");
        setSending(false);
      }
    );
  };

  const handleFeedback = (messageId: number, _feedback: "good" | "bad") => {
    void messageId;
  };

  const handleLogout = async () => {
    await logout();
    useAuthStore.getState().clear();
    navigate("/");
  };

  return (
    <div className="chat-layout">
      {hasEmergency && (
        <div className="emergency-banner">
          🚨 응급 상황이라면 즉시 119에 신고하세요.
          <button onClick={() => setHasEmergency(false)}>닫기</button>
        </div>
      )}

      <ChatSidebar
        selectedId={selectedSession?.id ?? null}
        onSelect={loadSession}
        onNewSession={(s) => {
          setSelectedSession(s);
          setMessages([]);
          setError(null);
        }}
        refreshKey={sidebarRefresh}
      />

      <main className="chat-main">
        <header className="chat-header">
          <h2>{selectedSession?.title ?? "AI 헬스케어 챗봇"}</h2>
          <div className="chat-header-actions">
            <Link to="/health-profile" className="btn-profile">건강 프로필</Link>
            <button className="btn-logout" onClick={handleLogout}>로그아웃</button>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            ⚠️ {error}
            <button onClick={() => { setError(null); setSending(false); }}>
              재시도
            </button>
          </div>
        )}

        {selectedSession ? (
          <>
            <ChatWindow
              messages={messages}
              streamingContent={streamingContent}
              onFeedback={handleFeedback}
            />
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
