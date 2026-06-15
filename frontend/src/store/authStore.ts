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
  ageRange?: string;
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
  isAuthenticated: boolean;
  isOnboarded: boolean;
  user: UserInfo | null;
  hasSeenDisclaimer: boolean;
  medicalProfile: MedicalProfile | null;
  setAuthenticated: (v: boolean) => void;
  setIsOnboarded: (v: boolean) => void;
  setUser: (user: UserInfo | null) => void;
  setHasSeenDisclaimer: (v: boolean) => void;
  setMedicalProfile: (profile: MedicalProfile) => void;
  clearMedicalProfile: () => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      isOnboarded: false,
      user: null,
      hasSeenDisclaimer: false,
      medicalProfile: null,
      setAuthenticated: (v) => set({ isAuthenticated: v }),
      setIsOnboarded: (v) => set({ isOnboarded: v }),
      setUser: (user) => set({ user }),
      setHasSeenDisclaimer: (v) => set({ hasSeenDisclaimer: v }),
      setMedicalProfile: (profile) => set({ medicalProfile: profile }),
      clearMedicalProfile: () => set({ medicalProfile: null }),
      clear: () =>
        set({
          isAuthenticated: false,
          isOnboarded: false,
          user: null,
          hasSeenDisclaimer: false,
          medicalProfile: null,
        }),
    }),
    {
      name: "medi-mate-auth",
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        isOnboarded: state.isOnboarded,
        hasSeenDisclaimer: state.hasSeenDisclaimer,
        medicalProfile: state.medicalProfile,
      }),
    },
  ),
);
