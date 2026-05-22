import { request } from "@/lib/api";
import type { UserInfoResponse } from "@/types/api";

interface KakaoLoginUrlResponse {
  auth_url: string;
}

interface TokenResponse {
  access_token: string;
}

interface LoginResponse {
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

export function login(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function signup(data: {
  email: string;
  password: string;
  name: string;
  gender: "MALE" | "FEMALE";
  birth_date: string;
  phone_number: string;
}): Promise<void> {
  return request<void>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function logout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
}

export function getMe(): Promise<UserInfoResponse> {
  return request<UserInfoResponse>("/users/me");
}
