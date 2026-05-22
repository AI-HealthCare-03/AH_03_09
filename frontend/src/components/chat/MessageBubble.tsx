import type { ChatMessageResponse } from "@/types/api";

interface Props {
  message: ChatMessageResponse;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-2xl whitespace-pre-wrap rounded-lg px-4 py-3 text-sm ${
          isUser ? "bg-slate-900 text-white" : "border border-slate-200 bg-white text-slate-900"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
