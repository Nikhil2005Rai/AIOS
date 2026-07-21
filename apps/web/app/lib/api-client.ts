const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function createApiClient(token: string | null) {
  return async function api<T>(endpoint: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? data);
      throw new Error(detail || "Request failed");
    }
    return data as T;
  };
}
