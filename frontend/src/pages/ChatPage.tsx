import { useState, useEffect, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import ChatSidebar from "../components/ChatSidebar";
import ChatWindow from "../components/ChatWindow";
import ChatInput from "../components/ChatInput";
import { getSessionDetail, streamMessage } from "../api/chat";
import { logout } from "../api/auth";
import type { ChatSession, ChatMessage } from "../types";

const EMERGENCY_KEYWORDS = ["응급", "119", "심정지", "의식 없", "숨 못 쉬"];

export default function ChatPage() {
  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [sending, setSending] = useState(false);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [hasEmergency, setHasEmergency] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<Set<number>>(new Set());
  const navigate = useNavigate();

  const loadSession = useCallback(async (session: ChatSession) => {
    setSelectedSession(session);
    setStreamingContent("");
    setError(null);
    const res = await getSessionDetail(session.id);
    setMessages(res.data.messages);
  }, []);

  useEffect(() => {
    if (selectedSession) loadSession(selectedSession);
  }, [selectedSession?.id, loadSession]); // loadSession 추가

  const handleSend = async (content: string) => {
    if (!selectedSession || sending) return;

    // 응급 키워드 감지
    const isEmergency = EMERGENCY_KEYWORDS.some(kw => content.includes(kw));
    setHasEmergency(isEmergency);

    setSending(true);
    setStreamingContent("");
    setError(null);

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
      (_messageId, title) => {
        // aiMsg, streamingContent 클로저 문제 → DB에서 정확한 값 로드
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
      },
      (detail) => {
        // alert 대신 error state
        setError(detail);
        setStreamingContent("");
        setSending(false);
      }
    );
  };

  const handleFeedback = (messageId: number, feedback: "good" | "bad") => {
    if (feedbackGiven.has(messageId)) return;
    setFeedbackGiven((prev) => new Set(prev).add(messageId));
    console.log(`[feedback] messageId=${messageId} feedback=${feedback}`);
  };

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <div className="chat-layout">
      {/* 응급 배너 */}
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

        {/* 오류 배너 */}
        {error && (
          <div className="error-banner">
            ⚠️ {error}
            <button onClick={() => {
              setError(null);
              setSending(false);
            }}>
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
