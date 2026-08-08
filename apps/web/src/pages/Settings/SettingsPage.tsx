import { useTranslation } from "react-i18next";

import { ApiError, API_BASE, describeError } from "../../api/client";
import { useAuth } from "../../app/providers/AuthProvider";
import { KeyValue, KeyValueList } from "../../components/data/KeyValue";
import { StatusChip } from "../../components/data/StatusChip";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { GlassPanel } from "../../components/glass/Panel";
import { Button } from "../../components/primitives/Button";
import { WorkspaceSplit } from "../../components/shell/AppShell";
import { LanguageSwitcher } from "../../components/shell/LanguageSwitcher";
import { ThemeToggle } from "../../components/shell/ThemeToggle";
import { MicDiagnostics } from "../../features/diagnostics/MicDiagnostics";
import {
  healthConnectionStatus,
  useHealth,
} from "../../features/diagnostics/useHealth";
import { useDocuments } from "../../features/knowledge-base/useKnowledge";

export function SettingsPage() {
  const health = useHealth();
  const documents = useDocuments();
  const { account } = useAuth();
  const { t } = useTranslation("shell");
  const { t: tCommon } = useTranslation("common");

  const knowledgeUnavailable =
    documents.error instanceof ApiError && documents.error.isNotImplemented;
  const availableSources =
    documents.data?.filter((item) => item.status === "AVAILABLE").length ?? null;

  const connection = healthConnectionStatus(health);

  return (
    <WorkspaceSplit>
      <div className="limen-scroll flex min-h-0 flex-1 flex-col gap-8">
        <header className="flex flex-col gap-2 px-1">
          <p className="type-label m-0">Diagnostics</p>
          <h2 className="type-h2 m-0 text-ice">Runtime surface</h2>
          <p className="type-body m-0 max-w-[54ch] text-text-2">
            Read-only status from the running backend. Values stay unknown when
            an endpoint is missing — nothing is invented on the client.
          </p>
        </header>

        <div className="grid grid-cols-1 content-start gap-6 xl:grid-cols-2 xl:gap-7">
          <GlassPanel title={t("preferences.title")} className="xl:col-span-2">
            <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between md:gap-8">
              <KeyValueList className="min-w-0 flex-1 md:max-w-md">
                <KeyValue
                  label={t("preferences.account")}
                  value={account?.email ?? null}
                  mono
                />
              </KeyValueList>
              <div className="flex flex-wrap items-center gap-6">
                <div className="flex flex-col gap-2">
                  <span className="type-label m-0">{tCommon("language.label")}</span>
                  <LanguageSwitcher />
                </div>
                <div className="flex flex-col gap-2">
                  <span className="type-label m-0">{tCommon("theme.label")}</span>
                  <ThemeToggle className="border border-glass-border bg-[var(--glass-surface)]" />
                </div>
              </div>
            </div>
            <p className="type-body-s mt-5 mb-0 leading-relaxed text-text-3">
              {t("preferences.hint")}
            </p>
          </GlassPanel>

          <GlassPanel
            title="Runtime model"
            actions={
              <StatusChip
                tone={connection === "connected" ? "expected" : "neutral"}
              >
                {connection === "connected" ? "Connected" : "Unavailable"}
              </StatusChip>
            }
          >
            {health.isPending ? (
              <LoadingState label="Reading backend health" rows={3} />
            ) : health.isError ? (
              <ErrorState
                title="Backend health unavailable"
                message={describeError(health.error)}
                onRetry={() => void health.refetch()}
              />
            ) : (
              <KeyValueList>
                <KeyValue label="Provider" value={health.data.llm_provider} />
                <KeyValue label="Model" value={health.data.llm_model} mono />
                <KeyValue label="Environment" value={health.data.app_env} />
                <KeyValue label="API version" value={health.data.version} mono />
              </KeyValueList>
            )}
            <p className="type-body-s mt-5 mb-0 leading-relaxed text-text-3">
              Selected by backend configuration. Read-only here so an evaluation
              run cannot be altered from the browser.
            </p>
          </GlassPanel>

          <GlassPanel title="Voice providers">
            <KeyValueList>
              <KeyValue label="Speech to text" value={null} />
              <KeyValue label="Text to speech" value={null} />
              <KeyValue label="Voice" value={null} />
            </KeyValueList>
            <p className="type-body-s mt-5 mb-0 leading-relaxed text-text-3">
              The health endpoint does not report speech providers yet, so these
              stay unknown rather than showing a guessed default.
            </p>
          </GlassPanel>

          <GlassPanel title="Microphone diagnostics">
            <MicDiagnostics />
          </GlassPanel>

          <GlassPanel title="Persistence">
            {health.isSuccess ? (
              <KeyValueList>
                <KeyValue
                  label="Database"
                  value={health.data.database.database}
                />
                <KeyValue
                  label="Schema version"
                  value={health.data.database.schema_version}
                  mono
                />
                <KeyValue
                  label="Path"
                  value={health.data.database.path}
                  mono
                />
              </KeyValueList>
            ) : (
              <p className="type-body m-0 text-text-3">
                Database details come from the health endpoint, which is not
                responding.
              </p>
            )}
          </GlassPanel>

          <GlassPanel title="Knowledge index">
            <KeyValueList>
              <KeyValue
                label="Indexed sources"
                value={knowledgeUnavailable ? null : availableSources}
                mono
              />
              <KeyValue
                label="Total documents"
                value={
                  knowledgeUnavailable ? null : (documents.data?.length ?? null)
                }
                mono
              />
            </KeyValueList>
            {knowledgeUnavailable && (
              <p className="type-body-s mt-5 mb-0 leading-relaxed text-amber">
                Knowledge endpoints are not on the running backend yet, so index
                health cannot be reported.
              </p>
            )}
          </GlassPanel>

          <GlassPanel title="Telemetry">
            <KeyValueList>
              <KeyValue label="P50 response latency" value={null} mono />
              <KeyValue label="P95 response latency" value={null} mono />
              <KeyValue label="Estimated cost per call" value={null} mono />
            </KeyValueList>
            <p className="type-body-s mt-5 mb-0 leading-relaxed text-text-3">
              Aggregates are produced from executed calls. Nothing appears until
              a real session has been measured.
            </p>
          </GlassPanel>

          <GlassPanel title="Build" className="xl:col-span-2">
            <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
              <KeyValueList className="min-w-0 flex-1 md:max-w-xl">
                <KeyValue label="Frontend mode" value={import.meta.env.MODE} />
                <KeyValue
                  label="API base"
                  value={API_BASE || "same origin"}
                  mono
                />
              </KeyValueList>
              <Button
                variant="secondary"
                size="md"
                onClick={() => {
                  void health.refetch();
                  void documents.refetch();
                }}
              >
                Re-run diagnostics
              </Button>
            </div>
          </GlassPanel>
        </div>
      </div>
    </WorkspaceSplit>
  );
}
