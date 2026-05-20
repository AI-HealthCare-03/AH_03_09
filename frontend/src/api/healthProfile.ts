import api from "./client";

export interface HealthProfileData {
  primary_conditions: string[];
  allergies: string[];
  current_medications: string[];
  lifestyle_exercise: "REGULAR" | "IRREGULAR" | "NONE";
  lifestyle_smoking: boolean;
  lifestyle_alcohol: "NONE" | "MODERATE" | "HEAVY";
}

export const getHealthProfile = () => api.get<HealthProfileData>("/health-profile");

export const updateHealthProfile = (data: Partial<HealthProfileData>) =>
  api.patch<HealthProfileData>("/health-profile", data);
