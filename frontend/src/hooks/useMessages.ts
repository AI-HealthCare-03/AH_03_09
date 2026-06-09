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
  const [delayMessage, setDelayMessage] = useState<string | null>(null);
  const lastParamsRef = { sessionId: "", content: "", guideId: null as string | null | undefined };

  const mutate = async ({ sessionId, content, guideId }: { sessionId: string; content: string; guideId?: string | null }) => {
    lastParamsRef.sessionId = sessionId;
    lastParamsRef.content = content;
    lastParamsRef.guideId = guideId;
    setIsPending(true);
    setStreamingContent("");
    setError(null);
    setDelayMessage(null);

    await streamMessage(
      sessionId,
      content,
      guideId,
      (chunk) => setStreamingContent((prev) => prev + chunk),
      (_messageId, _title) => {
        qc.invalidateQueries({ queryKey: messagesKey(sessionId) });
        qc.invalidateQueries({ queryKey: SESSIONS_KEY });
        setStreamingContent("");
        setDelayMessage(null);
        setIsPending(false);
      },
      (detail) => {
        setError(detail);
        setStreamingContent("");
        setDelayMessage(null);
        setIsPending(false);
      },
      (detail) => setDelayMessage(detail),
    );
  };

  const retry = () => {
    if (lastParamsRef.sessionId && lastParamsRef.content) {
      mutate({ sessionId: lastParamsRef.sessionId, content: lastParamsRef.content, guideId: lastParamsRef.guideId });
    }
  };

  return { mutate, retry, streamingContent, isPending, error, delayMessage };
}
