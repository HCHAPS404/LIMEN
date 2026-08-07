import { useQuery } from "@tanstack/react-query";

import { fetchHealth } from "../api/health";

export function SettingsPage() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 10_000,
  });

  return (
    <section className="panel" aria-labelledby="settings-title">
      <h1 id="settings-title">Ajustes / Diagnóstico</h1>
      <p>Estado del runtime y declaración del modelo. Health API conectada.</p>
      <div className="status-row">
        {health.isLoading && <span className="status-chip">Comprobando API…</span>}
        {health.isError && (
          <span className="status-chip" data-tone="bad">
            API no disponible
          </span>
        )}
        {health.data && (
          <>
            <span className="status-chip" data-tone="ok">
              API {health.data.status}
            </span>
            <span className="status-chip">
              LLM {health.data.llm_provider}/{health.data.llm_model}
            </span>
            <span className="status-chip">v{health.data.version}</span>
            <span className="status-chip">
              DB {health.data.database.database ?? "unknown"}
            </span>
          </>
        )}
      </div>
      {health.isError && (
        <p className="muted" style={{ marginTop: "1rem" }}>
          Arranca el backend con <code>make dev-api</code>.
        </p>
      )}
    </section>
  );
}
