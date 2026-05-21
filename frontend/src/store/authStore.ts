import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface UserInfo {
  id: number;
  kakao_id: string;
  email: string | null;
  name: string | null;
}

export interface MedicalProfile {
  nickname: string;
  gender: "M" | "F";
  birthdate: string; // ISO YYYY-MM-DD
  heightCm: number;
  weightKg: number;
  existingDiagnoses?: string;
  bloodPressure?: { systolic: number; diastolic: number };
}

interface AuthState {
  accessToken: string | null;
  user: UserInfo | null;
  hasSeenDisclaimer: boolean;
  termsAcceptedAt: string | null;
  onboardingCompletedAt: string | null;
  medicalProfile: MedicalProfile | null;
  setToken: (token: string) => void;
  setUser: (user: UserInfo | null) => void;
  setHasSeenDisclaimer: (v: boolean) => void;
  setTermsAccepted: () => void;
  setOnboardingCompleted: (profile: MedicalProfile) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      hasSeenDisclaimer: false,
      termsAcceptedAt: null,
      onboardingCompletedAt: null,
      medicalProfile: null,
      setToken: (token) => set({ accessToken: token }),
      setUser: (user) => set({ user }),
      setHasSeenDisclaimer: (v) => set({ hasSeenDisclaimer: v }),
      setTermsAccepted: () => set({ termsAcceptedAt: new Date().toISOString() }),
      setOnboardingCompleted: (profile) =>
        set({
          medicalProfile: profile,
          onboardingCompletedAt: new Date().toISOString(),
        }),
      clear: () =>
        set({
          accessToken: null,
          user: null,
          hasSeenDisclaimer: false,
          termsAcceptedAt: null,
          onboardingCompletedAt: null,
          medicalProfile: null,
        }),
    }),
    {
      name: "medi-mate-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        hasSeenDisclaimer: state.hasSeenDisclaimer,
        termsAcceptedAt: state.termsAcceptedAt,
        onboardingCompletedAt: state.onboardingCompletedAt,
        medicalProfile: state.medicalProfile,
      }),
    },
  ),
);
