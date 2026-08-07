export type HealthResponse = {
  status: string;
  version: string;
  app_env: string;
  llm_provider: string;
  llm_model: string;
  database: {
    database?: string;
    schema_version?: string;
    path?: string;
  };
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed (${response.status})`);
  }
  return (await response.json()) as HealthResponse;
}
