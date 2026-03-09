/**
 * JWT-aware API client for CR8 backend.
 *
 * Wraps fetch with automatic Bearer token injection, token refresh on 401,
 * and typed JSON parsing. All API calls go through this client.
 */

/**
 * Access token stored in memory only — never persisted to localStorage.
 * On page reload, the httpOnly refresh cookie reissues a new access token
 * via /api/auth/refresh. This prevents XSS-based token exfiltration.
 */
let accessToken: string | null = null;

export function getToken(): string | null {
  return accessToken;
}

export function setToken(token: string): void {
  accessToken = token;
}

export function clearToken(): void {
  accessToken = null;
}

/** Try to refresh the access token using the httpOnly refresh cookie. */
export async function refreshToken(): Promise<boolean> {
  try {
    const res = await fetch("/api/auth/refresh", {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return false;
    const data = await res.json();
    setToken(data.access_token);
    return true;
  } catch {
    return false;
  }
}

export class ApiError extends Error {
  status: number;
  statusText: string;
  body?: unknown;

  constructor(status: number, statusText: string, body?: unknown) {
    super(`${status} ${statusText}`);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.body = body;
  }
}

/**
 * Make an authenticated API request. Automatically retries once on 401
 * by attempting a token refresh.
 */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const doFetch = async (): Promise<Response> => {
    const token = getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    // Only set Content-Type for non-FormData bodies
    if (options.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    return fetch(path, {
      ...options,
      headers,
      credentials: "include",
    });
  };

  let res = await doFetch();

  // On 401, try refreshing the token once
  if (res.status === 401) {
    const refreshed = await refreshToken();
    if (refreshed) {
      res = await doFetch();
    }
  }

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      // Response may not be JSON
    }
    throw new ApiError(res.status, res.statusText, body);
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}
