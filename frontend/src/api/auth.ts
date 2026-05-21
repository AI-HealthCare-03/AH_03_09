import { request } from "@/lib/api";

interface KakaoLoginUrlResponse {
  auth_url: string;
}

interface TokenResponse {
  access_token: string;
}

export function fetchKakaoLoginUrl(): Promise<KakaoLoginUrlResponse> {
  return request<KakaoLoginUrlResponse>("/auth/kakao/login");
}

export function exchangeKakaoCode(code: string): Promise<TokenResponse> {
  return request<TokenResponse>(`/auth/kakao/callback?code=${encodeURIComponent(code)}`, {
    method: "POST",
  });
}
