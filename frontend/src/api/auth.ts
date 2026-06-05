import { request } from "@/lib/api";
import type { UserInfoResponse } from "@/types/api";

interface KakaoLoginUrlResponse {
  auth_url: string;
}

interface KakaoCallbackResponse {
  is_onboarded: boolean;
}

export function fetchKakaoLoginUrl(): Promise<KakaoLoginUrlResponse> {
  return request<KakaoLoginUrlResponse>("/auth/kakao/login");
}

export function exchangeKakaoCode(code: string): Promise<KakaoCallbackResponse> {
  return request<KakaoCallbackResponse>(`/auth/kakao/callback?code=${encodeURIComponent(code)}`, {
    method: "POST",
  });
}

export function logout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
}

export function getMe(): Promise<UserInfoResponse> {
  return request<UserInfoResponse>("/users/me");
}

export function completeOnboarding(): Promise<void> {
  return request<void>("/users/me/onboarding", { method: "POST" });
}
