import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { callKeys, listCalls } from "../../api/calls";
import { ApiError, describeError } from "../../api/client";
import { RiskBadge } from "../../components/data/RiskBadge";
import { StatusChip } from "../../components/data/StatusChip";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { InspectorPanel, SolidPanel } from "../../components/glass/Panel";
import { Button } from "../../components/primitives/Button";
import { WorkspaceSplit } from "../../components/shell/AppShell";
import { DecisionCard } from "../../features/traceability/DecisionCard";
import { TraceTimeline } from "../../features/traceability/TraceTimeline";
import { useTrace } from "../../features/traceability/useTrace";
import type { TraceEventRecord } from "../../api/types";

export function TracePage() {
  const { callId } = useParams<{ callId?: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("trace");
  const trace = useTrace(callId);
  const [selected, setSelected] = useState<TraceEventRecord | null>(null);
  const recent = useQuery({
    queryKey: callKeys.list(),
    queryFn: ({ signal }) => listCalls(signal),
    enabled: !callId,
  });

  const events = trace.data?.events ?? [];

  useEffect(() => {
    setSelected(null);
  }, [callId]);

  const notFound =
    trace.error instanceof ApiError &&
    (trace.error.status === 404 || trace.error.code === "call_not_found");
  const endpointMissing =
    trace.error instanceof ApiError && trace.error.isNotImplemented;

  return (
    <WorkspaceSplit
      inspector={
        callId && selected ? (
          <InspectorPanel title={t("inspector")} scroll className="h-full">
            <DecisionCard event={selected} />
          </InspectorPanel>
        ) : undefined
      }
    >
      <SolidPanel
        title={t("timeline")}
        actions={
          trace.data ? (
            <div className="flex items-center gap-2">
              <RiskBadge risk={trace.data.final_risk} size="sm" />
              {trace.data.escalated && (
                <StatusChip tone="escalation">{t("escalated")}</StatusChip>
              )}
            </div>
          ) : undefined
        }
        scroll
        className="min-h-0 flex-1"
      >
        {!callId ? (
          <div className="flex flex-col gap-8">
            <EmptyState
              density="inline"
              eyebrow="TRAZA"
              title={t("pickTitle")}
              description={t("pickBody")}
              action={
                <Button variant="secondary" asChild>
                  <Link to="/sessions">{t("browseSessions")}</Link>
                </Button>
              }
            />
            {recent.isSuccess && recent.data.length > 0 && (
              <div className="flex flex-col gap-3">
                <p className="type-label m-0 text-text-3">{t("recent")}</p>
                <ul className="m-0 flex list-none flex-col p-0">
                  {recent.data.slice(0, 8).map((call) => (
                    <li
                      key={call.call_id}
                      className="border-b border-[color-mix(in_oklab,var(--glass-border)_50%,transparent)] last:border-b-0"
                    >
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-4 py-3.5 text-left transition-colors hover:bg-[var(--glass-highlight)]"
                        onClick={() => navigate(`/trace/${call.call_id}`)}
                      >
                        <span className="type-body text-ice">
                          {call.patient_alias}
                        </span>
                        <RiskBadge risk={call.final_risk} size="sm" />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : trace.isPending ? (
          <LoadingState label={t("timeline")} rows={5} />
        ) : trace.isError ? (
          endpointMissing ? (
            <EmptyState
              density="inline"
              eyebrow="TRAZA"
              title={t("loadError")}
              description={describeError(trace.error)}
            />
          ) : (
            <ErrorState
              title={t("loadError")}
              message={
                notFound
                  ? `Call ${callId} was not found.`
                  : describeError(trace.error)
              }
              onRetry={() => void trace.refetch()}
            />
          )
        ) : events.length === 0 ? (
          <EmptyState
            density="inline"
            title={t("emptyEvents")}
            description={`Call ${callId}`}
          />
        ) : (
          <TraceTimeline
            events={events}
            selectedId={selected?.event_id ?? null}
            onSelect={setSelected}
          />
        )}
      </SolidPanel>
    </WorkspaceSplit>
  );
}
