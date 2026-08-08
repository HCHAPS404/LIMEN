import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError, describeError } from "../../api/client";
import type { TraceEventRecord } from "../../api/types";
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

export function TracePage() {
  const { callId } = useParams<{ callId?: string }>();
  const trace = useTrace(callId);
  const [selected, setSelected] = useState<TraceEventRecord | null>(null);

  const events = trace.data?.events ?? [];

  useEffect(() => {
    setSelected(null);
  }, [callId]);

  const endpointMissing =
    trace.error instanceof ApiError && trace.error.isNotImplemented;

  return (
    <WorkspaceSplit
      inspector={
        <InspectorPanel title="Inspector" scroll className="h-full">
          <DecisionCard event={selected} />
        </InspectorPanel>
      }
    >
      <SolidPanel
        title="Timeline"
        actions={
          trace.data ? (
            <div className="flex items-center gap-2">
              <RiskBadge risk={trace.data.final_risk} size="sm" />
              {trace.data.escalated && (
                <StatusChip tone="escalation">Escalated</StatusChip>
              )}
            </div>
          ) : undefined
        }
        scroll
        className="min-h-0 flex-1"
      >
        {!callId ? (
          <EmptyState
            eyebrow="TRAZA"
            title="Choose a call to audit"
            description="Every decision, retrieval, and safety evaluation is recorded per call. Open a session to inspect its reasoning chain."
            action={
              <Button variant="secondary" asChild>
                <Link to="/sessions">Browse sessions</Link>
              </Button>
            }
          />
        ) : trace.isPending ? (
          <LoadingState label="Loading trace" rows={5} />
        ) : trace.isError ? (
          endpointMissing ? (
            <EmptyState
              eyebrow="Not yet"
              title="Trace API not available"
              description={`The backend does not expose a trace for ${callId} yet. Decision history is never reconstructed on the client.`}
            />
          ) : (
            <ErrorState
              title="Could not load trace"
              message={describeError(trace.error)}
              onRetry={() => void trace.refetch()}
            />
          )
        ) : events.length === 0 ? (
          <EmptyState
            title="No recorded steps"
            description={`Call ${callId} exists but has no trace events. Nothing is inferred to fill the gap.`}
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
