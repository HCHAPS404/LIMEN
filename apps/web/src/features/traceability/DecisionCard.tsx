import { useTranslation } from "react-i18next";

import type { TraceEventRecord } from "../../api/types";
import { EvidenceCitation } from "../../components/data/EvidenceCitation";
import { Metric, MetricStrip } from "../../components/data/Metric";
import { RiskBadge } from "../../components/data/RiskBadge";
import { riskMeaning } from "../../components/data/riskPresentation";
import { EmptyState } from "../../components/feedback/EmptyState";
import { formatTimestamp } from "../../lib/format";
import { resolveTraceStageView } from "./traceStage";

export function DecisionCard({ event }: { event: TraceEventRecord | null }) {
  const { t } = useTranslation("trace");

  if (!event) {
    return (
      <EmptyState
        density="inline"
        eyebrow={t("inspector")}
        title={t("emptyInspectTitle")}
        description={t("emptyInspectBody")}
      />
    );
  }

  const view = resolveTraceStageView(event.stage);
  const metrics = event.metrics;

  return (
    <div className="flex min-h-0 flex-col gap-5">
      <div className="flex flex-col gap-2">
        <span className="type-label" style={{ color: view.accent }}>
          {view.label}
        </span>
        <h3 className="type-h3 m-0 text-white-ice">{event.label}</h3>
        <span className="type-body-s tabular text-text-3">
          Sequence #{event.sequence} · {formatTimestamp(event.timestamp)}
        </span>
        {event.detail && (
          <p className="type-body m-0 text-text-2">{event.detail}</p>
        )}
      </div>

      {event.risk && (
        <div className="flex flex-col gap-2 border-t border-glass-border pt-4">
          <span className="type-label">Safety decision</span>
          <RiskBadge risk={event.risk} size="md" showMeaning />
          <p className="type-body-s m-0 text-text-2">{riskMeaning(event.risk)}</p>
          {event.escalate && (
            <p className="type-body-s m-0 font-medium text-coral">
              Escalation to a human clinician was requested.
            </p>
          )}
        </div>
      )}

      {event.reasons && event.reasons.length > 0 && (
        <div className="flex flex-col gap-2 border-t border-glass-border pt-4">
          <span className="type-label">Activated rules</span>
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {event.reasons.map((reason) => (
              <li key={reason} className="type-body-s tabular text-text-2">
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {event.evidence && event.evidence.length > 0 && (
        <div className="flex flex-col gap-2 border-t border-glass-border pt-4">
          <span className="type-label">Evidence</span>
          <div className="flex flex-col gap-2">
            {event.evidence.map((chunk) => (
              <EvidenceCitation key={chunk.chunk_id} chunk={chunk} />
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-3 border-t border-glass-border pt-4">
        <span className="type-label">Measured cost</span>
        <MetricStrip className="grid-cols-2 xl:grid-cols-2">
          <Metric
            label="Latency"
            value={metrics?.latency_ms ?? null}
            unit="ms"
            hint="Turn round trip"
          />
          <Metric
            label="LLM calls"
            value={metrics?.llm_calls ?? null}
            hint="Model invocations"
          />
          <Metric
            label="Input tokens"
            value={metrics?.input_tokens ?? null}
            hint="Prompt tokens"
          />
          <Metric
            label="Output tokens"
            value={metrics?.output_tokens ?? null}
            hint="Completion tokens"
          />
          <Metric
            label="RAG queries"
            value={metrics?.rag_queries ?? null}
            hint="Retrieval calls"
            tone="evidence"
          />
          <Metric
            label="Est. cost"
            value={
              metrics?.estimated_cost_usd !== null &&
              metrics?.estimated_cost_usd !== undefined
                ? `$${metrics.estimated_cost_usd.toFixed(4)}`
                : null
            }
            hint="Derived from token usage"
          />
        </MetricStrip>
      </div>
    </div>
  );
}
