import { API_BASE, ApiError, withAuthRetry } from "@/lib/withAuthRetry";

export { ApiError } from "@/lib/withAuthRetry";

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await withAuthRetry(path, () =>
    fetch(`${API_BASE}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...init.headers,
      },
    }),
  );

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
