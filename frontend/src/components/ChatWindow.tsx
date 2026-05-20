import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";

interface Props {
  messages: ChatMessage[];
  streamingContent: string;
}

export default function ChatWindow({ messages, streamingContent }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

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
        </div>
      ))}
      {streamingContent && (
        <div className="message assistant">
          <div className="message-bubble streaming">
            {streamingContent}
            <span className="cursor" />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
