import { apiJson, apiRequest } from "./client";

export type AccountResponse = {
  account_id: string;
  email: string;
  display_name: string;
  created_at: string;
};

export type SessionResponse = {
  account: AccountResponse;
  expires_at: string;
};

export const authKeys = {
  me: ["auth", "me"] as const,
};

/** The session token never reaches this layer: it is an httpOnly cookie. */
export function fetchAccount(signal?: AbortSignal): Promise<AccountResponse> {
  return apiRequest<AccountResponse>("/api/auth/me", { signal });
}

export function register(input: {
  email: string;
  password: string;
  displayName: string;
}): Promise<SessionResponse> {
  return apiJson<SessionResponse>("/api/auth/register", {
    email: input.email,
    password: input.password,
    display_name: input.displayName,
  });
}

export function login(input: {
  email: string;
  password: string;
}): Promise<SessionResponse> {
  return apiJson<SessionResponse>("/api/auth/login", input);
}

export function logout(): Promise<void> {
  return apiRequest<void>("/api/auth/logout", { method: "POST" });
}
