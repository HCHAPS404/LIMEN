import { apiRequest } from "./client";
import type { HealthResponse } from "./types";

export const healthKeys = {
  root: ["health"] as const,
};

export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health", { signal });
}

export type { HealthResponse };
