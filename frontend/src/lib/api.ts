import { env } from "@/lib/env";
import { useAuthStore } from "@/store/authStore";

const API_BASE = `${env.VITE_API_BASE_URL}/api/v1`;

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: string,
  ) {
    super(`API ${status}: ${body}`);
    this.name = "ApiError";
  }
}

let refreshInFlight: Promise<string | null> | null = null;

async function callRefresh(): Promise<string | null> {
  const res = await fetch(`${API_BASE}/auth/token/refresh`, {
    credentials: "include",
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

function dedupedRefresh(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = callRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const doFetch = (token: string | null) =>
    fetch(`${API_BASE}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });

  let res = await doFetch(useAuthStore.getState().accessToken);

  if (res.status === 401 && !path.startsWith("/auth/")) {
    const refreshed = await dedupedRefresh();
    if (refreshed) {
      useAuthStore.getState().setToken(refreshed);
      res = await doFetch(refreshed);
    } else {
      useAuthStore.getState().clear();
      window.location.href = "/login";
      throw new Error("session expired");
    }
  }

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
