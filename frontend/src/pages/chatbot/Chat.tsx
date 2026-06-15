import { BotIcon, PlusIcon, UserIcon } from "lucide-react";
import { useEffect, useRef } from "react";
import Markdown from "react-markdown";
import { useNavigate } from "react-router-dom";
import InputComposer from "@/components/chat/InputComposer";
import MessageBubble from "@/components/chat/MessageBubble";
import SessionSidebar from "@/components/chat/SessionSidebar";
import { Button } from "@/components/ui/button";
import { useChat } from "@/hooks/useChat";
import { useChatStore } from "@/store/chatStore";

const SUGGESTED_QUESTIONS = [
  "이 약의 부작용이 있나요?",
  "공복에 먹어도 되는 약인가요?",
  "약을 먹고 술을 마셔도 되나요?",
  "처방받은 약을 임의로 끊어도 될까요?",
];

export default function Chat() {
  const navigate = useNavigate();
  const setCurrentSessionId = useChatStore((s) => s.setCurrentSessionId);
  const setGuideId = useChatStore((s) => s.setGuideId);
  const guideId = useChatStore((s) => s.guideId);
  const {
    messages,
    isLoading,
    currentSessionId,
    lastAssistantId,
    optimisticUserMsg,
    feedbackGiven,
    feedbackError,
    setFeedbackError,
    submitError,
    setSubmitError,
    retryCount,
    busy,
    streamMut,
    guidePromptShown,
    markGuidePromptShown,
    handleSubmit,
    handleRetry,
    handleFeedback,
    handleLogout,
  } = useChat();

  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = (smooth = false) => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: smooth ? "smooth" : "auto",
    });
  };

  // 메시지 전송 직후 즉시 스크롤 (입력창 겹침 방지)
  useEffect(() => {
    if (optimisticUserMsg) scrollToBottom();
  }, [optimisticUserMsg]);

  // 스트리밍 중 자동 스크롤 (instant — smooth는 청크마다 튀어서 겹침 발생)
  useEffect(() => {
    if (!streamMut.streamingContent) return;
    scrollToBottom();
  }, [streamMut.streamingContent]);

  // 응답 완료 후 최종 스크롤 (부드럽게)
  useEffect(() => {
    if (messages.length === 0) return;
    scrollToBottom(true);
  }, [messages.length]);

  return (
    <div className="flex h-dvh flex-col bg-slate-50 text-slate-900">
      <div className="flex flex-1 overflow-hidden">
        <SessionSidebar onLogout={handleLogout} />

        <main className="flex flex-1 flex-col overflow-hidden">
          <header className="flex h-14 items-center border-b border-slate-200 bg-white px-4">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => { setCurrentSessionId(null); setGuideId(null); }}
              aria-label="새 대화"
              className="md:hidden"
            >
              <PlusIcon className="size-4" />
              새 대화
            </Button>
            <div className="ml-auto flex items-center">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => navigate("/profile")}
                aria-label="내 정보"
              >
                <UserIcon />
              </Button>
            </div>
          </header>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-6">
            {currentSessionId && isLoading ? (
              <div className="space-y-4">
                <div className="flex items-start gap-2.5">
                  <div className="mt-1 size-8 shrink-0 animate-pulse rounded-full bg-slate-200" />
                  <div className="space-y-2 pt-1">
                    <div className="h-3 w-48 animate-pulse rounded bg-slate-200" />
                    <div className="h-3 w-64 animate-pulse rounded bg-slate-200" />
                    <div className="h-3 w-40 animate-pulse rounded bg-slate-200" />
                  </div>
                </div>
                <div className="flex flex-row-reverse items-start gap-2.5">
                  <div className="mt-1 size-8 shrink-0 animate-pulse rounded-full bg-slate-200" />
                  <div className="space-y-2 pt-1">
                    <div className="h-3 w-32 animate-pulse rounded bg-slate-200" />
                  </div>
                </div>
                <div className="flex items-start gap-2.5">
                  <div className="mt-1 size-8 shrink-0 animate-pulse rounded-full bg-slate-200" />
                  <div className="space-y-2 pt-1">
                    <div className="h-3 w-56 animate-pulse rounded bg-slate-200" />
                    <div className="h-3 w-44 animate-pulse rounded bg-slate-200" />
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {!optimisticUserMsg && !streamMut.isPending && !streamMut.streamingContent && (!currentSessionId || messages.length === 0) ? (
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
                    {guideId ? (
                      <div className="w-full max-w-md rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
                        처방전 가이드가 연동되어 있습니다. 처방약·복약 정보에 대해 질문해 보세요.
                      </div>
                    ) : (
                      <div className="w-full max-w-md rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-600">
                        처방전 가이드와 연동하면 OCR 인식된 처방약 정보를 기반으로 답변받을 수 있어요.{" "}
                        <button
                          type="button"
                          onClick={() => navigate("/health-guide")}
                          className="font-medium underline underline-offset-2 hover:text-blue-800"
                        >
                          가이드 페이지로 이동
                        </button>
                      </div>
                    )}
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
                ) : null}

                {messages.map((m) => (
                  <MessageBubble
                    key={m.id}
                    message={m}
                    onFeedback={
                      m.role === "assistant" && m.id === lastAssistantId && !streamMut.isPending
                        ? handleFeedback
                        : undefined
                    }
                    feedbackGiven={feedbackGiven.get(m.id)}
                  />
                ))}

                {streamMut.actionCard === "guide_prompt" && !guidePromptShown && (
                  <div className="flex items-start gap-2.5">
                    <div className="mt-1 grid size-8 shrink-0 place-items-center rounded-full bg-primary text-white">
                      <BotIcon className="size-4" />
                    </div>
                    <div className="rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3">
                      <p className="mb-2 text-sm text-slate-600">어떻게 하시겠어요?</p>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => { markGuidePromptShown(); navigate("/health-guide"); }}
                          className="rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-xs font-medium text-primary hover:bg-primary/10"
                        >
                          🏥 건강 가이드로 넘어가기
                        </button>
                        <button
                          type="button"
                          onClick={() => { markGuidePromptShown(); streamMut.dismissAction(); }}
                          className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100"
                        >
                          💬 가이드 없이 챗봇 사용
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {optimisticUserMsg && (
                  <MessageBubble
                    message={{
                      id: -1,
                      role: "user",
                      content: optimisticUserMsg,
                      created_at: new Date().toISOString(),
                    }}
                  />
                )}

                {streamMut.isPending && !streamMut.streamingContent && (
                  <div className="flex items-start gap-2.5">
                    <div className="mt-1 grid size-8 shrink-0 place-items-center rounded-full bg-primary text-white">
                      <BotIcon className="size-4" />
                    </div>
                    <div className="rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3">
                      <div className="flex gap-1">
                        <span className="size-2 animate-bounce rounded-full bg-slate-400 [animation-delay:0ms]" />
                        <span className="size-2 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]" />
                        <span className="size-2 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]" />
                      </div>
                    </div>
                  </div>
                )}

                {streamMut.streamingContent && (
                  <div className="flex flex-col items-start">
                    <div className="max-w-2xl rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900">
                      <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:mt-2 prose-headings:mb-1 prose-strong:font-semibold prose-code:rounded prose-code:bg-slate-100 prose-code:px-1 prose-code:py-0.5 prose-code:text-xs">
                        <Markdown>{streamMut.streamingContent}</Markdown>
                      </div>
                      <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-slate-400" />
                    </div>
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
                    {retryCount >= 3 ? (
                      <span className="ml-auto shrink-0 text-xs text-red-400">잠시 후 다시 시도해주세요.</span>
                    ) : (
                      <button
                        type="button"
                        onClick={handleRetry}
                        disabled={streamMut.isPending}
                        className="ml-auto shrink-0 rounded border border-red-300 px-2 py-1 text-xs hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        다시 시도 ({retryCount}/3)
                      </button>
                    )}
                  </div>
                )}

                {submitError && (
                  <div className="flex items-center justify-between rounded-md bg-red-50 px-4 py-2 text-sm text-red-600">
                    <span>⚠️ {submitError}</span>
                    <button type="button" onClick={() => setSubmitError(null)} className="ml-4 shrink-0 text-red-400 hover:text-red-600">✕</button>
                  </div>
                )}
              </div>
            )}
          </div>

          {feedbackError && (
            <div className="flex items-center justify-between border-t border-orange-200 bg-orange-50 px-4 py-2 text-sm text-orange-700">
              <span>{feedbackError}</span>
              <button
                type="button"
                onClick={() => setFeedbackError(null)}
                className="ml-4 shrink-0 text-orange-500 hover:text-orange-700"
              >
                ✕
              </button>
            </div>
          )}
          <InputComposer onSubmit={handleSubmit} disabled={busy} />
        </main>
      </div>
    </div>
  );
}
