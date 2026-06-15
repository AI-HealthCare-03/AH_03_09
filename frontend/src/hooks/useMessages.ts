import { useCallback, useRef, useState } from "react";
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
  const [actionCard, setActionCard] = useState<string | null>(null);
  const lastParamsRef = useRef({ sessionId: "", content: "", guideId: null as string | null | undefined });
  const abortRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setStreamingContent("");
    setIsPending(false);
    setDelayMessage(null);
    setActionCard(null);
  }, []);

  const dismissAction = useCallback(() => setActionCard(null), []);

  const mutate = async ({ sessionId, content, guideId }: { sessionId: string; content: string; guideId?: string | null }) => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    lastParamsRef.current.sessionId = sessionId;
    lastParamsRef.current.content = content;
    lastParamsRef.current.guideId = guideId;
    setIsPending(true);
    setStreamingContent("");
    setError(null);
    setDelayMessage(null);
    setActionCard(null);

    await streamMessage(
      sessionId,
      content,
      guideId,
      (chunk) => setStreamingContent((prev) => prev + chunk),
      (_messageId, _title) => {
        abortRef.current = null;
        qc.refetchQueries({ queryKey: messagesKey(sessionId) }).finally(() => {
          setStreamingContent("");
          setDelayMessage(null);
          setIsPending(false);
        });
        qc.invalidateQueries({ queryKey: SESSIONS_KEY });
      },
      (detail) => {
        abortRef.current = null;
        setError(detail);
        setStreamingContent("");
        setDelayMessage(null);
        setIsPending(false);
      },
      (detail) => setDelayMessage(detail),
      controller.signal,
      (action) => setActionCard(action),
    );
  };

  const retry = () => {
    const { sessionId, content, guideId } = lastParamsRef.current;
    if (sessionId && content) {
      mutate({ sessionId, content, guideId });
    }
  };

  return { mutate, retry, cancel, dismissAction, streamingContent, isPending, error, delayMessage, actionCard };
}
