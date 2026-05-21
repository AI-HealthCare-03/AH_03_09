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

/**
 * Runs a fetch with the current access token. On 401, transparently refreshes
 * via the HttpOnly refresh cookie and retries once. If refresh fails, clears
 * the auth store and redirects to /login.
 *
 * `path` is only used to decide whether to attempt the refresh (auth endpoints
 * are excluded). The caller's `doFetch` is responsible for building the URL.
 */
export async function withAuthRetry(
  path: string,
  doFetch: (token: string | null) => Promise<Response>,
): Promise<Response> {
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

  return res;
}
