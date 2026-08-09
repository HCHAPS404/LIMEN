import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation("sessions");
  const calls = useQuery({
    queryKey: callKeys.list(),
    queryFn: ({ signal }) => listCalls(signal),
  });

  const endpointMissing =
    calls.error instanceof ApiError && calls.error.isNotImplemented;

  return (
    <WorkspaceSplit>
      <SolidPanel
        title={t("title")}
        scroll
        padded={false}
        className="min-h-0 flex-1"
      >
        {calls.isPending && (
          <div className="p-5">
            <LoadingState label={t("title")} rows={4} />
          </div>
        )}

        {calls.isError && (
          <div className="p-5">
            {endpointMissing ? (
              <EmptyState
                density="inline"
                eyebrow={t("title")}
                title={t("loadError")}
                description={describeError(calls.error)}
              />
            ) : (
              <ErrorState
                title={t("loadError")}
                message={describeError(calls.error)}
                onRetry={() => void calls.refetch()}
              />
            )}
          </div>
        )}

        {calls.isSuccess &&
          (calls.data.length === 0 ? (
            <EmptyState
              density="inline"
              eyebrow={t("title")}
              title={t("emptyTitle")}
              description={t("emptyBody")}
              action={
                <Button variant="primary" asChild>
                  <Link to="/call">{t("startCall")}</Link>
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
