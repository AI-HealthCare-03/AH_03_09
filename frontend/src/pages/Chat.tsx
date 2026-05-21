import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import InputComposer from "@/components/chat/InputComposer";
import MessageBubble from "@/components/chat/MessageBubble";
import SessionSidebar from "@/components/chat/SessionSidebar";
import ProfileModal from "@/components/common/ProfileModal";
import { useMessages, useSendMessage } from "@/hooks/useMessages";
import { useCreateSession } from "@/hooks/useSessions";
import { useAuthStore } from "@/store/authStore";
import { useChatStore } from "@/store/chatStore";

export default function Chat() {
  const navigate = useNavigate();
  const clear = useAuthStore((s) => s.clear);
  const currentSessionId = useChatStore((s) => s.currentSessionId);
  const setCurrentSessionId = useChatStore((s) => s.setCurrentSessionId);

  const [profileOpen, setProfileOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: messagesData, isLoading } = useMessages(currentSessionId);
  const sendMut = useSendMessage();
  const createMut = useCreateSession();

  const messages = messagesData?.messages ?? [];

  const messageCount = messages.length;
  useEffect(() => {
    if (messageCount === 0) return;
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messageCount]);

  const handleLogout = () => {
    clear();
    navigate("/login", { replace: true });
  };

  const handleWithdrawn = () => {
    clear();
    setProfileOpen(false);
    navigate("/login", { replace: true });
  };

  const handleSubmit = async (content: string) => {
    let sessionId = currentSessionId;
    if (!sessionId) {
      const session = await createMut.mutateAsync(undefined);
      sessionId = session.id;
      setCurrentSessionId(sessionId);
    }
    await sendMut.mutateAsync({ sessionId, content });
  };

  const busy = sendMut.isPending || createMut.isPending;

  return (
    <div className="flex h-dvh bg-slate-50 text-slate-900">
      <SessionSidebar onProfileClick={() => setProfileOpen(true)} onLogout={handleLogout} />

      <main className="flex flex-1 flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6">
          {!currentSessionId ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              왼쪽에서 대화를 선택하거나 새 대화를 시작하세요.
            </div>
          ) : isLoading ? (
            <p className="text-sm text-slate-500">불러오는 중…</p>
          ) : messages.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              메시지를 입력해 대화를 시작하세요.
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}
              {sendMut.isPending && <div className="text-sm text-slate-400">답변 생성 중…</div>}
            </div>
          )}
        </div>

        <InputComposer onSubmit={handleSubmit} disabled={busy} />
      </main>

      <ProfileModal
        open={profileOpen}
        onClose={() => setProfileOpen(false)}
        onWithdrawn={handleWithdrawn}
      />
    </div>
  );
}
