import { API_BASE, ApiError, withAuthRetry } from "@/lib/withAuthRetry";

export async function postMultipart<T>(
  path: string,
  formData: FormData,
  signal?: AbortSignal,
): Promise<T> {
  const res = await withAuthRetry(path, () =>
    fetch(`${API_BASE}${path}`, {
      method: "POST",
      body: formData,
      credentials: "include",
      signal,
    }),
  );

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
