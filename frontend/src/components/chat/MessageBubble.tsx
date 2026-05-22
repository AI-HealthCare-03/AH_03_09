import type { ChatMessageResponse } from "@/types/api";

interface Props {
  message: ChatMessageResponse;
  onFeedback?: (messageId: number, feedback: "good" | "bad") => void;
  feedbackGiven?: boolean;
}

export default function MessageBubble({ message, onFeedback, feedbackGiven }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-2xl whitespace-pre-wrap rounded-lg px-4 py-3 text-sm ${
          isUser ? "bg-slate-900 text-white" : "border border-slate-200 bg-white text-slate-900"
        }`}
      >
        {message.content}
      </div>

      {!isUser && (
        <div className="mt-1 space-y-1">
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
  );
}
