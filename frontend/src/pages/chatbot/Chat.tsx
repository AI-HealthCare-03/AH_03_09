import { ArrowLeftIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import InputComposer from "@/components/chat/InputComposer";
import MessageBubble from "@/components/chat/MessageBubble";
import SessionSidebar from "@/components/chat/SessionSidebar";
import { Button } from "@/components/ui/button";
import { useMessages, useStreamMessage } from "@/hooks/useMessages";
import { useCreateSession } from "@/hooks/useSessions";
import { useAuthStore } from "@/store/authStore";
import { useChatStore } from "@/store/chatStore";

const EMERGENCY_KEYWORDS = ["응급", "119", "심정지", "의식 없", "숨 못 쉬"];

export default function Chat() {
  const navigate = useNavigate();
  const clear = useAuthStore((s) => s.clear);
  const currentSessionId = useChatStore((s) => s.currentSessionId);
  const setCurrentSessionId = useChatStore((s) => s.setCurrentSessionId);

  const scrollRef = useRef<HTMLDivElement>(null);
  const [hasEmergency, setHasEmergency] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<Set<number>>(new Set());

  const { data: messagesData, isLoading } = useMessages(currentSessionId);
  const streamMut = useStreamMessage();
  const createMut = useCreateSession();

  const messages = messagesData?.messages ?? [];

  useEffect(() => {
    if (messages.length === 0 && !streamMut.streamingContent) return;
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.length, streamMut.streamingContent]);

  const handleLogout = () => {
    clear();
    navigate("/", { replace: true });
  };

  const handleSubmit = async (content: string) => {
    const isEmergency = EMERGENCY_KEYWORDS.some((kw) => content.includes(kw));
    setHasEmergency(isEmergency);

    let sessionId = currentSessionId;
    if (!sessionId) {
      const session = await createMut.mutateAsync(undefined);
      sessionId = session.id;
      setCurrentSessionId(sessionId);
    }
    await streamMut.mutate({ sessionId, content });
  };

  const handleFeedback = (messageId: number, _feedback: "good" | "bad") => {
    setFeedbackGiven((prev) => new Set(prev).add(messageId));
  };

  const busy = streamMut.isPending || createMut.isPending;

  return (
    <div className="flex h-dvh flex-col bg-slate-50 text-slate-900">
      {hasEmergency && (
        <div className="flex items-center justify-between bg-red-600 px-4 py-2 text-sm font-medium text-white">
          🚨 응급 상황이라면 즉시 119에 신고하세요.
          <button
            type="button"
            onClick={() => setHasEmergency(false)}
            className="ml-4 underline opacity-80 hover:opacity-100"
          >
            닫기
          </button>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <SessionSidebar onProfileClick={() => navigate("/profile")} onLogout={handleLogout} />

        <main className="flex flex-1 flex-col overflow-hidden">
          <header className="flex h-14 items-center gap-2 border-b border-slate-200 bg-white px-4">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => navigate("/home")}
              aria-label="홈으로"
            >
              <ArrowLeftIcon className="size-4" />
              홈으로
            </Button>
          </header>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-6">
            {!currentSessionId ? (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">
                왼쪽에서 대화를 선택하거나 새 대화를 시작하세요.
              </div>
            ) : isLoading ? (
              <p className="text-sm text-slate-500">불러오는 중…</p>
            ) : (
              <div className="space-y-4">
                {messages.length === 0 && !streamMut.streamingContent && (
                  <div className="flex h-full items-center justify-center text-sm text-slate-500">
                    메시지를 입력해 대화를 시작하세요.
                  </div>
                )}

                {messages.map((m) => (
                  <MessageBubble
                    key={m.id}
                    message={m}
                    onFeedback={m.role === "assistant" ? handleFeedback : undefined}
                    feedbackGiven={feedbackGiven.has(m.id)}
                  />
                ))}

                {streamMut.streamingContent && (
                  <div className="flex flex-col items-start">
                    <div className="max-w-2xl whitespace-pre-wrap rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900">
                      {streamMut.streamingContent}
                      <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-slate-400" />
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      ⚕️ 본 답변은 참고용이며, 정확한 진단은 전문가와 상담하세요.
                    </p>
                  </div>
                )}

                {streamMut.error && (
                  <div className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-600">
                    ⚠️ {streamMut.error}
                  </div>
                )}
              </div>
            )}
          </div>

          <InputComposer onSubmit={handleSubmit} disabled={busy} />
        </main>
      </div>
    </div>
  );
}
