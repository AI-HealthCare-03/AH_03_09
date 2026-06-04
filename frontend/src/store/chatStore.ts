import { create } from "zustand";

interface ChatState {
  currentSessionId: string | null;
  setCurrentSessionId: (id: string | null) => void;
  guideId: string | null;
  setGuideId: (id: string | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  currentSessionId: null,
  setCurrentSessionId: (id) => set({ currentSessionId: id }),
  guideId: null,
  setGuideId: (id) => set({ guideId: id }),
}));
