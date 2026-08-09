import { apiJson, apiRequest } from "./client";
import type { CallSummary } from "./types";

export const callKeys = {
  all: ["calls"] as const,
  list: () => [...callKeys.all, "list"] as const,
  detail: (callId: string) => [...callKeys.all, "detail", callId] as const,
  summary: (callId: string) => [...callKeys.all, "summary", callId] as const,
};

export function listCalls(signal?: AbortSignal): Promise<CallSummary[]> {
  return apiRequest<CallSummary[]>("/api/calls", { signal });
}

export function createCall(input?: {
  patientAlias?: string;
  procedure?: string | null;
  postoperativeDay?: number | null;
}): Promise<CallSummary> {
  return apiJson<CallSummary>("/api/calls", {
    patient_alias: input?.patientAlias ?? "Paciente",
    procedure: input?.procedure ?? null,
    postoperative_day: input?.postoperativeDay ?? null,
  });
}

export function finishCall(callId: string): Promise<CallSummary> {
  return apiRequest<CallSummary>(
    `/api/calls/${encodeURIComponent(callId)}/finish`,
    { method: "POST" },
  );
}

export function getCallSummary(callId: string, signal?: AbortSignal) {
  return apiRequest<{
    call: CallSummary;
    summary: Record<string, unknown> | null;
    clinical_state: Record<string, unknown>;
    metrics: Record<string, unknown>;
    turns: unknown[];
  }>(`/api/calls/${encodeURIComponent(callId)}/summary`, { signal });
}

/** Realtime voice session. Cookie auth is sent automatically by the browser. */
export function callSocketUrl(callId: string): string {
  const base = import.meta.env.VITE_API_BASE ?? window.location.origin;
  const url = new URL(base, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/api/calls/${encodeURIComponent(callId)}/stream`;
  return url.toString();
}
