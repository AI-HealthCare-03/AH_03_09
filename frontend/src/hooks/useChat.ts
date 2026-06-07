import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { submitFeedback } from "@/api/chat";
import { useMessages, useStreamMessage } from "@/hooks/useMessages";
import { useCreateSession } from "@/hooks/useSessions";
import { useAuthStore } from "@/store/authStore";
import { useChatStore } from "@/store/chatStore";

export function useChat() {
  const navigate = useNavigate();
  const clear = useAuthStore((s) => s.clear);
  const currentSessionId = useChatStore((s) => s.currentSessionId);
  const setCurrentSessionId = useChatStore((s) => s.setCurrentSessionId);
  const guideId = useChatStore((s) => s.guideId);

  const [feedbackGiven, setFeedbackGiven] = useState<Set<number>>(new Set());
  const [optimisticUserMsg, setOptimisticUserMsg] = useState<string | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  const { data: messagesData, isLoading } = useMessages(currentSessionId);
  const streamMut = useStreamMessage();
  const createMut = useCreateSession();

  const messages = messagesData?.messages ?? [];
  const lastAssistantId = [...messages].reverse().find((m) => m.role === "assistant")?.id;
  const busy = streamMut.isPending || createMut.isPending;

  useEffect(() => {
    setOptimisticUserMsg(null);
  }, [messages.length]);

  const handleLogout = () => {
    clear();
    navigate("/", { replace: true });
  };

  const handleSubmit = async (content: string) => {
    setOptimisticUserMsg(content);
    let sessionId = currentSessionId;
    if (!sessionId) {
      const title = content.length > 20 ? content.slice(0, 20) + "…" : content;
      const session = await createMut.mutateAsync(title);
      sessionId = session.id;
      setCurrentSessionId(sessionId);
    }
    await streamMut.mutate({ sessionId, content, guideId });
  };

  const handleFeedback = async (messageId: number, feedback: "good" | "bad") => {
    if (!currentSessionId) return;
    try {
      await submitFeedback(currentSessionId, messageId, feedback);
      setFeedbackGiven((prev) => new Set(prev).add(messageId));
    } catch {
      setFeedbackError("피드백 전송에 실패했습니다. 다시 시도해주세요.");
    }
  };

  return {
    messages,
    isLoading,
    currentSessionId,
    lastAssistantId,
    optimisticUserMsg,
    feedbackGiven,
    feedbackError,
    setFeedbackError,
    busy,
    streamMut,
    handleSubmit,
    handleFeedback,
    handleLogout,
  };
}
