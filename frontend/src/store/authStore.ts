import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface UserInfo {
  id: number;
  kakao_id: string;
  email: string | null;
  name: string | null;
}

export interface MedicalProfile {
  gender?: "M" | "F" | "OTHER";
  birthDate?: string;
  heightCm: number;
  weightKg: number;
  existingDiagnoses?: string;
  bloodPressure?: { systolic: number; diastolic: number };
  allergies?: string[];
  currentMedications?: string[];
  lifestyleExercise?: "REGULAR" | "IRREGULAR" | "NONE";
  lifestyleSmoking?: boolean;
  lifestyleAlcohol?: "NONE" | "MODERATE" | "HEAVY";
}

interface AuthState {
  accessToken: string | null;
  user: UserInfo | null;
  hasSeenDisclaimer: boolean;
  medicalProfile: MedicalProfile | null;
  setToken: (token: string) => void;
  setUser: (user: UserInfo | null) => void;
  setHasSeenDisclaimer: (v: boolean) => void;
  setMedicalProfile: (profile: MedicalProfile) => void;
  clearMedicalProfile: () => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      hasSeenDisclaimer: false,
      medicalProfile: null,
      setToken: (token) => set({ accessToken: token }),
      setUser: (user) => set({ user }),
      setHasSeenDisclaimer: (v) => set({ hasSeenDisclaimer: v }),
      setMedicalProfile: (profile) => set({ medicalProfile: profile }),
      clearMedicalProfile: () => set({ medicalProfile: null }),
      clear: () =>
        set({
          accessToken: null,
          user: null,
          hasSeenDisclaimer: false,
          medicalProfile: null,
        }),
    }),
    {
      name: "medi-mate-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        hasSeenDisclaimer: state.hasSeenDisclaimer,
        medicalProfile: state.medicalProfile,
      }),
    },
  ),
);
