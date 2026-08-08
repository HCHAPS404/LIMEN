import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { callKeys, listCalls } from "../../api/calls";
import { ApiError, describeError } from "../../api/client";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { SolidPanel } from "../../components/glass/Panel";
import { Button } from "../../components/primitives/Button";
import { WorkspaceSplit } from "../../components/shell/AppShell";
import { SessionsTable } from "../../features/sessions/SessionsTable";

export function SessionsPage() {
  const calls = useQuery({
    queryKey: callKeys.list(),
    queryFn: ({ signal }) => listCalls(signal),
  });

  const endpointMissing =
    calls.error instanceof ApiError && calls.error.isNotImplemented;

  return (
    <WorkspaceSplit>
      <SolidPanel
        title="Completed calls"
        scroll
        padded={false}
        className="min-h-0 flex-1"
      >
        {calls.isPending && (
          <div className="p-5">
            <LoadingState label="Loading sessions" rows={4} />
          </div>
        )}

        {calls.isError && (
          <div className="p-5">
            {endpointMissing ? (
              <EmptyState
                eyebrow="Not yet"
                title="Sessions API not available"
                description="The backend does not expose call history yet. No placeholder sessions are shown."
              />
            ) : (
              <ErrorState
                title="Could not load sessions"
                message={describeError(calls.error)}
                onRetry={() => void calls.refetch()}
              />
            )}
          </div>
        )}

        {calls.isSuccess &&
          (calls.data.length === 0 ? (
            <EmptyState
              eyebrow="Quiet"
              title="No calls recorded"
              description="Completed follow-up calls appear here with their final risk, escalation outcome, and a link to the full decision trace."
              action={
                <Button variant="primary" asChild>
                  <Link to="/call">Start a call</Link>
                </Button>
              }
            />
          ) : (
            <SessionsTable calls={calls.data} />
          ))}
      </SolidPanel>
    </WorkspaceSplit>
  );
}
