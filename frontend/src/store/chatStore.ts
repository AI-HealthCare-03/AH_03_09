import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ChatState {
  currentSessionId: string | null;
  setCurrentSessionId: (id: string | null) => void;
  guideId: string | null;
  setGuideId: (id: string | null) => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      currentSessionId: null,
      setCurrentSessionId: (id) => set({ currentSessionId: id }),
      guideId: null,
      setGuideId: (id) => set({ guideId: id }),
    }),
    {
      name: "medi-mate-chat",
      partialize: (state) => ({
        currentSessionId: state.currentSessionId,
      }),
    },
  ),
);
