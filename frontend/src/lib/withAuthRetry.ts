import { toast } from "sonner";
import { env } from "@/lib/env";
import { useAuthStore } from "@/store/authStore";

export const API_BASE = `${env.VITE_API_BASE_URL}/api/v1`;

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: string,
  ) {
    super(`API ${status}: ${body}`);
    this.name = "ApiError";
  }
}

let refreshInFlight: Promise<boolean> | null = null;

async function callRefresh(): Promise<boolean> {
  const res = await fetch(`${API_BASE}/auth/token/refresh`, {
    credentials: "include",
  });
  return res.ok;
}

function dedupedRefresh(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = callRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function withAuthRetry(
  path: string,
  doFetch: () => Promise<Response>,
): Promise<Response> {
  let res = await doFetch();

  if (res.status === 401 && !path.startsWith("/auth/")) {
    const refreshed = await dedupedRefresh();
    if (refreshed) {
      res = await doFetch();
    } else {
      useAuthStore.getState().clear();
      toast.error("세션이 만료되었습니다. 다시 로그인해 주세요.");
      window.location.href = "/";
      throw new Error("session expired");
    }
  }

  return res;
}
