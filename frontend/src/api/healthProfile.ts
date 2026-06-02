import { request } from "@/lib/api";
import type { HealthProfileResponse, HealthProfileUpdateRequest } from "@/types/api";

export function fetchHealthProfile(): Promise<HealthProfileResponse> {
  return request<HealthProfileResponse>("/health-profile");
}

export function updateHealthProfile(data: HealthProfileUpdateRequest): Promise<HealthProfileResponse> {
  return request<HealthProfileResponse>("/health-profile", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
