import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";

import type { TraceEventRecord } from "../../api/types";
import { EvidenceCitation } from "../../components/data/EvidenceCitation";
import { Metric, MetricStrip } from "../../components/data/Metric";
import { RiskBadge } from "../../components/data/RiskBadge";
import { EmptyState } from "../../components/feedback/EmptyState";
import { formatTimestamp } from "../../lib/format";
import {
  collectPayloadFacts,
  collectPresentMetrics,
  eventTypeKey,
  resolveEventType,
  resolveTraceAccent,
  resolveTraceCategoryKey,
} from "./eventPresentation";
import { translateSafetyReason } from "./translateSafetyReason";

type TraceT = TFunction<"trace">;

/** Dynamic keys (event types, payload facts) are not in the typed key union. */
function soft(
  t: TraceT,
  key: string,
  defaultValue: string,
  options?: Record<string, string | number>,
): string {
  return String(t(key as never, { defaultValue, ...options }));
}

const METRIC_COPY: Record<string, { label: string; hint: string }> = {
  duration: { label: "metrics.duration", hint: "metrics.durationHint" },
  latency: { label: "metrics.latency", hint: "metrics.latencyHint" },
  clinical: { label: "metrics.clinical", hint: "metrics.clinicalHint" },
  uncertainty: { label: "metrics.uncertainty", hint: "metrics.uncertaintyHint" },
  retrieval: { label: "metrics.retrieval", hint: "metrics.retrievalHint" },
  safety: { label: "metrics.safety", hint: "metrics.safetyHint" },
  generation: { label: "metrics.generation", hint: "metrics.generationHint" },
  dense: { label: "metrics.dense", hint: "metrics.denseHint" },
  lexical: { label: "metrics.lexical", hint: "metrics.lexicalHint" },
  fusion: { label: "metrics.fusion", hint: "metrics.fusionHint" },
  llmCalls: { label: "metrics.llmCalls", hint: "metrics.llmCallsHint" },
  inputTokens: { label: "metrics.inputTokens", hint: "metrics.inputTokensHint" },
  outputTokens: {
    label: "metrics.outputTokens",
    hint: "metrics.outputTokensHint",
  },
  ragQueries: { label: "metrics.ragQueries", hint: "metrics.ragQueriesHint" },
  evidenceSelected: {
    label: "metrics.evidenceSelected",
    hint: "metrics.evidenceSelectedHint",
  },
  estCost: { label: "metrics.estCost", hint: "metrics.estCostHint" },
  voiceLatency: {
    label: "metrics.voiceLatency",
    hint: "metrics.voiceLatencyHint",
  },
  stt: { label: "metrics.stt", hint: "metrics.sttHint" },
  tts: { label: "metrics.tts", hint: "metrics.ttsHint" },
};

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

  const eventType = resolveEventType(event);
  const typeKey = eventTypeKey(eventType);
  const categoryKey = resolveTraceCategoryKey(event);
  const accent = resolveTraceAccent(event);
  const title = soft(t, `events.${typeKey}.title`, t("events.unknown.title"));
  const summary = soft(
    t,
    `events.${typeKey}.summary`,
    t("events.unknown.summary"),
  );
  const category = soft(t, `categories.${categoryKey}`, t("categories.step"));
  const metrics = collectPresentMetrics(event);
  const facts = collectPayloadFacts(event.payload);
  const status = event.status ?? "ok";

  return (
    <div className="flex min-h-0 flex-col gap-5">
      <div className="flex flex-col gap-2">
        <span className="type-label" style={{ color: accent }}>
          {category}
        </span>
        <h3 className="type-h3 m-0 text-white-ice">{title}</h3>
        <span className="type-body-s tabular text-text-3">
          {t("sequence", {
            sequence: event.sequence,
            time: formatTimestamp(event.timestamp),
          })}
        </span>
        {status !== "ok" && (
          <span className="type-body-s font-medium text-coral">
            {status === "error"
              ? t("statusError")
              : status === "skipped"
                ? t("statusSkipped")
                : status}
          </span>
        )}
      </div>

      <div className="flex flex-col gap-2 border-t border-glass-border pt-4">
        <span className="type-label">{t("sections.whatHappened")}</span>
        <p className="type-body m-0 text-text-2">{summary}</p>
      </div>

      {event.detail ? (
        <div className="flex flex-col gap-2 border-t border-glass-border pt-4">
          <span className="type-label">{t("sections.detail")}</span>
          <p className="type-body m-0 whitespace-pre-wrap text-text-2">
            {event.detail}
          </p>
        </div>
      ) : null}

      {event.risk ? (
        <div className="flex flex-col gap-2 border-t border-glass-border pt-4">
          <span className="type-label">{t("sections.safety")}</span>
          <RiskBadge risk={event.risk} size="md" showMeaning />
          {event.escalate ? (
            <p className="type-body-s m-0 font-medium text-coral">
              {t("sections.escalated")}
            </p>
          ) : null}
        </div>
      ) : null}

      {event.reasons && event.reasons.length > 0 ? (
        <div className="flex flex-col gap-2 border-t border-glass-border pt-4">
          <span className="type-label">{t("sections.reasons")}</span>
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {event.reasons.map((reason) => (
              <li key={reason} className="type-body-s text-text-2">
                {translateSafetyReason(reason, t)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {event.evidence && event.evidence.length > 0 ? (
        <div className="flex flex-col gap-2 border-t border-glass-border pt-4">
          <span className="type-label">{t("sections.evidence")}</span>
          <div className="flex flex-col gap-2">
            {event.evidence.map((chunk) => (
              <EvidenceCitation key={chunk.chunk_id} chunk={chunk} />
            ))}
          </div>
        </div>
      ) : null}

      {facts.length > 0 ? (
        <div className="flex flex-col gap-2 border-t border-glass-border pt-4">
          <span className="type-label">{t("sections.facts")}</span>
          <dl className="m-0 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {facts.map((fact) => {
              const label = soft(
                t,
                `facts.${fact.key}`,
                fact.key.replaceAll("_", " "),
              );
              const value =
                fact.value === "true"
                  ? t("facts.true")
                  : fact.value === "false"
                    ? t("facts.false")
                    : fact.value;
              return (
                <div key={fact.key} className="flex min-w-0 flex-col gap-0.5">
                  <dt className="type-label m-0 text-text-3">{label}</dt>
                  <dd className="type-body-s m-0 break-words text-text-2">
                    {value}
                  </dd>
                </div>
              );
            })}
          </dl>
        </div>
      ) : null}

      {metrics.length > 0 ? (
        <div className="flex flex-col gap-3 border-t border-glass-border pt-4">
          <span className="type-label">{t("sections.measurements")}</span>
          <MetricStrip className="grid-cols-2 xl:grid-cols-2">
            {metrics.map((metric) => {
              const copy = METRIC_COPY[metric.key] ?? {
                label: "metrics.duration",
                hint: "metrics.durationHint",
              };
              return (
                <Metric
                  key={metric.key}
                  label={soft(t, copy.label, copy.label)}
                  value={metric.value}
                  unit={metric.unit}
                  hint={soft(t, copy.hint, copy.hint)}
                  emptyHint={t("metrics.notMeasured")}
                  tone={
                    metric.key === "ragQueries" ||
                    metric.key === "evidenceSelected"
                      ? "evidence"
                      : metric.key === "safety"
                        ? "audit"
                        : "default"
                  }
                />
              );
            })}
          </MetricStrip>
        </div>
      ) : (
        <div className="border-t border-glass-border pt-4">
          <p className="type-body-s m-0 text-text-3">{t("sections.noExtra")}</p>
        </div>
      )}
    </div>
  );
}
