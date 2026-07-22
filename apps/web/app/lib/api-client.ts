const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function createApiClient(tokenOrGetter: string | null | (() => Promise<string | null>)) {
  return async function api<T>(endpoint: string, init?: RequestInit): Promise<T> {
    let bearerToken: string | null = null;
    if (typeof tokenOrGetter === "function") {
      bearerToken = await tokenOrGetter();
    } else {
      bearerToken = tokenOrGetter;
    }
    if (!bearerToken && typeof window !== "undefined") {
      bearerToken = localStorage.getItem("aios_token");
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(bearerToken ? { Authorization: `Bearer ${bearerToken}` } : {}),
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
