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
  const [retryCount, setRetryCount] = useState(0);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { data: messagesData, isLoading } = useMessages(currentSessionId);
  const streamMut = useStreamMessage();
  const createMut = useCreateSession();

  const messages = messagesData?.messages ?? [];
  const lastAssistantId = [...messages].reverse().find((m) => m.role === "assistant")?.id;
  const busy = streamMut.isPending || createMut.isPending;

  useEffect(() => {
    setOptimisticUserMsg(null);
    setRetryCount(0);
  }, [messages.length]);

  const handleLogout = () => {
    clear();
    navigate("/", { replace: true });
  };

  const handleSubmit = async (content: string) => {
    setOptimisticUserMsg(content);
    setSubmitError(null);
    let sessionId = currentSessionId;
    if (!sessionId) {
      try {
        const title = content.length > 20 ? content.slice(0, 20) + "…" : content;
        const session = await createMut.mutateAsync(title);
        sessionId = session.id;
        setCurrentSessionId(sessionId);
      } catch {
        setOptimisticUserMsg(null);
        setSubmitError("대화를 시작할 수 없습니다. 다시 시도해주세요.");
        return;
      }
    }
    await streamMut.mutate({ sessionId, content, guideId });
  };

  const handleRetry = () => {
    if (retryCount >= 3) return;
    setRetryCount((prev) => prev + 1);
    streamMut.retry();
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
    submitError,
    setSubmitError,
    retryCount,
    busy,
    streamMut,
    handleSubmit,
    handleRetry,
    handleFeedback,
    handleLogout,
  };
}
