import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchMessages, sendMessage, streamMessage } from "@/api/chat";
import { SESSIONS_KEY } from "@/hooks/useSessions";

function messagesKey(sessionId: string) {
  return ["messages", sessionId] as const;
}

export function useMessages(sessionId: string | null) {
  return useQuery({
    queryKey: sessionId ? messagesKey(sessionId) : ["messages", "none"],
    queryFn: () => {
      if (!sessionId) throw new Error("sessionId required");
      return fetchMessages(sessionId);
    },
    enabled: !!sessionId,
  });
}

export function useSendMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, content }: { sessionId: string; content: string }) =>
      sendMessage(sessionId, content),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: messagesKey(variables.sessionId) });
      qc.invalidateQueries({ queryKey: SESSIONS_KEY });
    },
  });
}

export function useStreamMessage() {
  const qc = useQueryClient();
  const [streamingContent, setStreamingContent] = useState("");
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutate = async ({ sessionId, content }: { sessionId: string; content: string }) => {
    setIsPending(true);
    setStreamingContent("");
    setError(null);

    await streamMessage(
      sessionId,
      content,
      (chunk) => setStreamingContent((prev) => prev + chunk),
      (_messageId, _title) => {
        qc.invalidateQueries({ queryKey: messagesKey(sessionId) });
        qc.invalidateQueries({ queryKey: SESSIONS_KEY });
        setStreamingContent("");
        setIsPending(false);
      },
      (detail) => {
        setError(detail);
        setStreamingContent("");
        setIsPending(false);
      },
    );
  };

  return { mutate, streamingContent, isPending, error };
}
