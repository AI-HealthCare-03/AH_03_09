import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchMessages, sendMessage } from "@/api/chat";
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
