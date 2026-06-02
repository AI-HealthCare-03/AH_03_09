import { ArrowLeftIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import { useNavigate } from "react-router-dom";
import InputComposer from "@/components/chat/InputComposer";
import MessageBubble from "@/components/chat/MessageBubble";
import SessionSidebar from "@/components/chat/SessionSidebar";
import { Button } from "@/components/ui/button";
import { useMessages, useStreamMessage } from "@/hooks/useMessages";
import { useCreateSession } from "@/hooks/useSessions";
import { submitFeedback } from "@/api/chat";
import { useAuthStore } from "@/store/authStore";
import { useChatStore } from "@/store/chatStore";

const SUGGESTED_QUESTIONS = [
  "이 약의 부작용이 있나요?",
  "공복에 먹어도 되는 약인가요?",
  "약을 먹고 술을 마셔도 되나요?",
  "처방받은 약을 임의로 끊어도 될까요?",
];

export default function Chat() {
  const navigate = useNavigate();
  const clear = useAuthStore((s) => s.clear);
  const currentSessionId = useChatStore((s) => s.currentSessionId);
  const setCurrentSessionId = useChatStore((s) => s.setCurrentSessionId);

  const scrollRef = useRef<HTMLDivElement>(null);
  const [feedbackGiven, setFeedbackGiven] = useState<Set<number>>(new Set());

  const { data: messagesData, isLoading } = useMessages(currentSessionId);
  const streamMut = useStreamMessage();
  const { retry } = streamMut;
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
    let sessionId = currentSessionId;
    if (!sessionId) {
      const session = await createMut.mutateAsync(undefined);
      sessionId = session.id;
      setCurrentSessionId(sessionId);
    }
    await streamMut.mutate({ sessionId, content });
  };

  const handleFeedback = async (messageId: number, feedback: "good" | "bad") => {
    setFeedbackGiven((prev) => new Set(prev).add(messageId));
    if (currentSessionId) {
      await submitFeedback(currentSessionId, messageId, feedback).catch(() => null);
    }
  };

  const busy = streamMut.isPending || createMut.isPending;

  return (
    <div className="flex h-dvh flex-col bg-slate-50 text-slate-900">
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
                  <div className="flex h-full flex-col items-center justify-center gap-6 py-12">
                    <div className="flex flex-col items-center gap-3 text-center">
                      <div className="grid size-14 place-items-center rounded-2xl bg-primary/10 text-primary">
                        <span className="text-2xl">💊</span>
                      </div>
                      <div>
                        <p className="text-base font-semibold text-slate-800">
                          안녕하세요! 복약 도우미예요.
                        </p>
                        <p className="mt-1 text-sm text-slate-500">
                          약 복용법, 부작용, 상호작용 등 궁금한 점을 물어보세요.
                        </p>
                      </div>
                    </div>
                    <div className="grid w-full max-w-md grid-cols-2 gap-2">
                      {SUGGESTED_QUESTIONS.map((q) => (
                        <button
                          key={q}
                          type="button"
                          onClick={() => handleSubmit(q)}
                          className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-left text-xs text-slate-600 transition-colors hover:border-primary/50 hover:bg-primary/5 hover:text-primary"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
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
                    <div className="max-w-2xl rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900">
                      <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:mt-2 prose-headings:mb-1 prose-strong:font-semibold prose-code:rounded prose-code:bg-slate-100 prose-code:px-1 prose-code:py-0.5 prose-code:text-xs">
                        <Markdown>{streamMut.streamingContent}</Markdown>
                      </div>
                      <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-slate-400" />
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      ⚕️ 본 답변은 참고용이며, 정확한 진단은 전문가와 상담하세요.
                    </p>
                  </div>
                )}

                {streamMut.delayMessage && (
                  <div className="rounded-md bg-yellow-50 px-4 py-2 text-sm text-yellow-700">
                    ⏳ {streamMut.delayMessage}
                  </div>
                )}

                {streamMut.error && (
                  <div className="flex items-center gap-3 rounded-md bg-red-50 px-4 py-2 text-sm text-red-600">
                    <span>⚠️ {streamMut.error}</span>
                    <button
                      type="button"
                      onClick={retry}
                      className="ml-auto shrink-0 rounded border border-red-300 px-2 py-1 text-xs hover:bg-red-100"
                    >
                      다시 시도
                    </button>
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
