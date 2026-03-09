/**
 * Auth API functions — login, register, logout, fetch current user.
 */

import { apiFetch, setToken, clearToken } from "./client";

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
}

interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  expires_in: number;
}

interface RegisterResponse {
  user_id: string;
  email: string;
}

export async function login(email: string, password: string): Promise<User> {
  const data = await apiFetch<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(data.access_token);
  return fetchCurrentUser();
}

export async function register(
  email: string,
  password: string,
  displayName?: string,
): Promise<RegisterResponse> {
  return apiFetch<RegisterResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      display_name: displayName,
    }),
  });
}

export async function logout(): Promise<void> {
  try {
    await apiFetch<void>("/api/auth/logout", { method: "POST" });
  } finally {
    clearToken();
  }
}

export async function fetchCurrentUser(): Promise<User> {
  return apiFetch<User>("/api/auth/me");
}
