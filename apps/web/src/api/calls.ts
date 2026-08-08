import { apiRequest } from "./client";
import type { CallSummary } from "./types";

export const callKeys = {
  all: ["calls"] as const,
  list: () => [...callKeys.all, "list"] as const,
};

export function listCalls(signal?: AbortSignal): Promise<CallSummary[]> {
  return apiRequest<CallSummary[]>("/api/calls", { signal });
}

/** Realtime endpoint the voice session will attach to once the backend exposes it. */
export function callSocketUrl(callId: string): string {
  const base = import.meta.env.VITE_API_BASE ?? window.location.origin;
  const url = new URL(base, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/api/calls/${encodeURIComponent(callId)}/stream`;
  return url.toString();
}
