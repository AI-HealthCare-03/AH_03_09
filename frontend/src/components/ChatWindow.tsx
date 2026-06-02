import { useEffect, useRef, useState } from "react";
import type { ChatMessageResponse } from "@/types/api";

interface Props {
  messages: ChatMessageResponse[];
  streamingContent: string;
  onFeedback?: (messageId: number, feedback: "good" | "bad") => void;
}

export default function ChatWindow({ messages, streamingContent, onFeedback }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [feedbackGiven, setFeedbackGiven] = useState<Set<number>>(new Set());

  const handleFeedback = (messageId: number, feedback: "good" | "bad") => {
    if (feedbackGiven.has(messageId)) return;
    setFeedbackGiven((prev) => new Set(prev).add(messageId));
    onFeedback?.(messageId, feedback);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  return (
    <div className="chat-window">
      {messages.length === 0 && !streamingContent && (
        <div className="chat-empty">
          <p>건강에 대해 무엇이든 물어보세요.</p>
        </div>
      )}

      {messages.map((msg) => (
        <div key={msg.id} className={`message ${msg.role}`}>
          <div className="message-bubble">{msg.content}</div>

          {/* AI 응답에만 워터마크 + 피드백 버튼 */}
          {msg.role === "assistant" && (
            <>
              <div className="message-disclaimer">
                ⚕️ 본 답변은 참고용이며, 정확한 진단은 전문가와 상담하세요.
              </div>
              {onFeedback && (
                <div className="message-feedback">
                  <button
                    onClick={() => handleFeedback(msg.id, "good")}
                    disabled={feedbackGiven.has(msg.id)}
                  >
                    👍 도움됐어요
                  </button>
                  <button
                    onClick={() => handleFeedback(msg.id, "bad")}
                    disabled={feedbackGiven.has(msg.id)}
                  >
                    👎 도움 안됐어요
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      ))}

      {/* 스트리밍 중 */}
      {streamingContent && (
        <div className="message assistant">
          <div className="message-bubble streaming">
            {streamingContent}
            <span className="cursor" />
          </div>
          <div className="message-disclaimer">
            ⚕️ 본 답변은 참고용이며, 정확한 진단은 전문가와 상담하세요.
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
