import { BotIcon, UserIcon } from "lucide-react";
import Markdown from "react-markdown";
import type { ChatMessageResponse } from "@/types/api";

interface Props {
  message: ChatMessageResponse;
  onFeedback?: (messageId: number, feedback: "good" | "bad") => void;
  feedbackGiven?: boolean;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
}

export default function MessageBubble({ message, onFeedback, feedbackGiven }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-2.5 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div
        className={`mt-1 grid size-8 shrink-0 place-items-center rounded-full text-white ${
          isUser ? "bg-slate-700" : "bg-primary"
        }`}
      >
        {isUser ? <UserIcon className="size-4" /> : <BotIcon className="size-4" />}
      </div>

      <div className={`flex max-w-2xl flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm ${
            isUser
              ? "whitespace-pre-wrap rounded-tr-sm bg-slate-900 text-white"
              : "rounded-tl-sm border border-slate-200 bg-white text-slate-900"
          }`}
        >
          {isUser ? (
            message.content
          ) : (
            <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:mt-2 prose-headings:mb-1 prose-strong:font-semibold prose-code:rounded prose-code:bg-slate-100 prose-code:px-1 prose-code:py-0.5 prose-code:text-xs">
              <Markdown>{message.content}</Markdown>
            </div>
          )}
        </div>

        <span className="text-xs text-slate-400">{formatTime(message.created_at)}</span>

        {!isUser && (
          <div className="space-y-1">
            <p className="text-xs text-slate-400">
              ⚕️ 본 답변은 참고용이며, 정확한 진단은 전문가와 상담하세요.
            </p>
            {onFeedback && (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => !feedbackGiven && onFeedback(message.id, "good")}
                  disabled={feedbackGiven}
                  className="rounded border border-slate-200 px-2 py-0.5 text-xs text-slate-500 hover:border-slate-400 disabled:cursor-default disabled:opacity-50"
                >
                  {feedbackGiven ? "✓ 감사합니다" : "👍 도움됐어요"}
                </button>
                {!feedbackGiven && (
                  <button
                    type="button"
                    onClick={() => onFeedback(message.id, "bad")}
                    className="rounded border border-slate-200 px-2 py-0.5 text-xs text-slate-500 hover:border-slate-400"
                  >
                    👎 도움 안됐어요
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
