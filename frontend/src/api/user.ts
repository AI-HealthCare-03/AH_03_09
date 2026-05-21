import { request } from "@/lib/api";
import type { UserInfoResponse } from "@/types/api";

export const WITHDRAW_CONFIRMATION_TEXT = "회원탈퇴합니다";

export function fetchMe(): Promise<UserInfoResponse> {
  return request<UserInfoResponse>("/users/me");
}

export function withdrawMe(confirmationText: string): Promise<void> {
  return request<void>("/users/me", {
    method: "DELETE",
    body: JSON.stringify({ confirmation_text: confirmationText }),
  });
}
