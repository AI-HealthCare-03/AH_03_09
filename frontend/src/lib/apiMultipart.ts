import { API_BASE, ApiError, withAuthRetry } from "@/lib/withAuthRetry";

/**
 * Posts a FormData body to the API with automatic 401 refresh + retry.
 * Does NOT set Content-Type — the browser sets it (with boundary) for FormData.
 * Pass an AbortSignal to support cancellation during upload.
 */
export async function postMultipart<T>(
  path: string,
  formData: FormData,
  signal?: AbortSignal,
): Promise<T> {
  const res = await withAuthRetry(path, (token) =>
    fetch(`${API_BASE}${path}`, {
      method: "POST",
      body: formData,
      credentials: "include",
      signal,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }),
  );

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
