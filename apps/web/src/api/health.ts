import { apiRequest } from "./client";
import type { HealthResponse } from "./types";

export const healthKeys = {
  root: ["health"] as const,
};

export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health", { signal });
}

export type ReadyResponse = {
  status: string;
  checks: Record<string, string>;
};

export type ProvidersResponse = {
  llm: {
    provider: string;
    model: string;
    configured_provider?: string;
    configured_model?: string;
    reachable?: boolean | null;
    degraded_mode?: boolean;
    last_provider_error?: string | null;
    timeout_s?: number;
    secondary_enabled?: boolean;
    secondary_model?: string | null;
    safety_fallback?: string;
  };
  stt: {
    provider: string;
    model: string;
    reachable?: boolean | null;
    degraded_mode?: boolean;
    last_error?: string | null;
  };
  tts: {
    provider: string;
    model: string;
    voice?: string;
    reachable?: boolean | null;
    degraded_mode?: boolean;
    last_error?: string | null;
  };
  embedding: { provider: string; model: string };
};

export function fetchReady(signal?: AbortSignal): Promise<ReadyResponse> {
  return apiRequest<ReadyResponse>("/health/ready", { signal });
}

export function fetchProviders(
  signal?: AbortSignal,
): Promise<ProvidersResponse> {
  return apiRequest<ProvidersResponse>("/health/providers", { signal });
}

export type { HealthResponse };
