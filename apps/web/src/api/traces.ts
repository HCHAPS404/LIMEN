import { apiRequest } from "./client";
import type { CallTrace } from "./types";

export const traceKeys = {
  all: ["traces"] as const,
  detail: (callId: string) => [...traceKeys.all, callId] as const,
};

export function getTrace(callId: string, signal?: AbortSignal): Promise<CallTrace> {
  return apiRequest<CallTrace>(
    `/api/traces/${encodeURIComponent(callId)}`,
    { signal },
  );
}
