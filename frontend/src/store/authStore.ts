import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface UserInfo {
  id: number;
  kakao_id: string;
  email: string | null;
  name: string | null;
}

interface AuthState {
  accessToken: string | null;
  user: UserInfo | null;
  hasSeenDisclaimer: boolean;
  setToken: (token: string) => void;
  setUser: (user: UserInfo | null) => void;
  setHasSeenDisclaimer: (v: boolean) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      hasSeenDisclaimer: false,
      setToken: (token) => set({ accessToken: token }),
      setUser: (user) => set({ user }),
      setHasSeenDisclaimer: (v) => set({ hasSeenDisclaimer: v }),
      clear: () => set({ accessToken: null, user: null }),
    }),
    {
      name: "medi-mate-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        hasSeenDisclaimer: state.hasSeenDisclaimer,
      }),
    },
  ),
);
