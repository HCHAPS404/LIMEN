import { useQuery } from "@tanstack/react-query";
import { LogOut, Moon, Sun, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { ApiError, API_BASE, describeError } from "../../api/client";
import { fetchProviders, fetchReady } from "../../api/health";
import { useAuth } from "../../app/providers/AuthProvider";
import { useTheme, type Theme } from "../../app/providers/ThemeProvider";
import {
  useVoicePersona,
  type VoicePersonaId,
} from "../../app/providers/VoicePersonaProvider";
import { KeyValue, KeyValueList } from "../../components/data/KeyValue";
import { StatusChip } from "../../components/data/StatusChip";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { GlassPanel } from "../../components/glass/Panel";
import { Button } from "../../components/primitives/Button";
import { Dialog } from "../../components/primitives/Dialog";
import { WorkspaceSplit } from "../../components/shell/AppShell";
import { LanguageSwitcher } from "../../components/shell/LanguageSwitcher";
import { MicDiagnostics } from "../../features/diagnostics/MicDiagnostics";
import {
  healthConnectionStatus,
  useHealth,
} from "../../features/diagnostics/useHealth";
import { useDocuments } from "../../features/knowledge-base/useKnowledge";
import { cn } from "../../lib/cn";

/**
 * Settings is a single preference surface: appearance, language, account
 * identity, microphone check, and session actions. Runtime diagnostics stay
 * collapsed so the page does not read as an ops dashboard.
 */
export function SettingsPage() {
  const health = useHealth();
  const documents = useDocuments();
  const ready = useQuery({
    queryKey: ["health", "ready"],
    queryFn: ({ signal }) => fetchReady(signal),
    retry: false,
  });
  const providers = useQuery({
    queryKey: ["health", "providers"],
    queryFn: ({ signal }) => fetchProviders(signal),
    retry: false,
  });
  const {
    account,
    signOut,
    isSigningOut,
    deleteAccount,
    isDeletingAccount,
  } = useAuth();
  const { theme, setTheme } = useTheme();
  const { personaId, setPersonaId, personas } = useVoicePersona();
  const navigate = useNavigate();
  const { t } = useTranslation("shell");
  const { t: tCommon } = useTranslation("common");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const knowledgeUnavailable =
    documents.error instanceof ApiError && documents.error.isNotImplemented;
  const availableSources =
    documents.data?.filter((item) => item.status === "AVAILABLE").length ?? null;
  const connection = healthConnectionStatus(health);
  const busy = isSigningOut || isDeletingAccount;

  const themes: { id: Theme; label: string; icon: typeof Sun }[] = [
    { id: "dark", label: tCommon("theme.dark"), icon: Moon },
    { id: "light", label: tCommon("theme.light"), icon: Sun },
  ];

  return (
    <WorkspaceSplit scroll="page">
      <div className="mx-auto flex w-full max-w-[40rem] flex-col gap-5 pb-6">
        <header className="flex flex-col gap-2">
          <p className="type-eyebrow m-0 text-text-3">{t("nav.settings")}</p>
          <h2 className="type-h1 m-0 text-ice">{t("preferences.title")}</h2>
          <p className="type-body m-0 max-w-[36ch] text-text-2">
            {t("preferences.lead")}
          </p>
        </header>

        <GlassPanel padded={false} className="overflow-hidden">
          <section className="flex flex-col gap-4 border-b border-glass-border px-6 py-5">
            <div className="flex flex-col gap-1">
              <h3 className="type-label m-0 tracking-[0.14em]">
                {tCommon("theme.label")}
              </h3>
              <p className="type-body-s m-0 text-text-3">
                {t("preferences.themeHint")}
              </p>
            </div>
            <div
              className="grid grid-cols-2 gap-2"
              role="radiogroup"
              aria-label={tCommon("theme.label")}
            >
              {themes.map(({ id, label, icon: Icon }) => {
                const selected = theme === id;
                return (
                  <button
                    key={id}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    onClick={() => setTheme(id)}
                    className={cn(
                      "flex items-center gap-3 rounded-lg border px-3.5 py-3 text-left transition-colors",
                      selected
                        ? "border-action-glass-border bg-action-glass text-ice"
                        : "border-glass-border bg-[var(--glass-surface)] text-text-2 hover:border-[var(--glass-border-strong)] hover:text-ice",
                    )}
                  >
                    <Icon aria-hidden size={16} strokeWidth={1.6} />
                    <span className="text-[0.875rem] font-medium">{label}</span>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="flex flex-col gap-4 border-b border-glass-border px-6 py-5">
            <div className="flex flex-col gap-1">
              <h3 className="type-label m-0 tracking-[0.14em]">
                {t("preferences.voice")}
              </h3>
              <p className="type-body-s m-0 text-text-3">
                {t("preferences.voiceHint")}
              </p>
            </div>
            <div
              className="grid grid-cols-1 gap-2 sm:grid-cols-2"
              role="radiogroup"
              aria-label={t("preferences.voice")}
            >
              {personas.map((persona) => {
                const selected = personaId === persona.id;
                return (
                  <button
                    key={persona.id}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    onClick={() => setPersonaId(persona.id as VoicePersonaId)}
                    className={cn(
                      "flex flex-col gap-1 rounded-lg border px-3.5 py-3 text-left transition-colors",
                      selected
                        ? "border-action-glass-border bg-action-glass text-ice"
                        : "border-glass-border bg-[var(--glass-surface)] text-text-2 hover:border-[var(--glass-border-strong)] hover:text-ice",
                    )}
                  >
                    <span className="text-[0.875rem] font-medium">
                      {persona.displayName}
                    </span>
                    <span className="type-body-s m-0 text-text-3">
                      {persona.blurb}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="flex flex-col gap-3 border-b border-glass-border px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-col gap-1">
              <h3 className="type-label m-0 tracking-[0.14em]">
                {tCommon("language.label")}
              </h3>
              <p className="type-body-s m-0 text-text-3">
                {t("preferences.languageHint")}
              </p>
            </div>
            <LanguageSwitcher />
          </section>

          <section className="flex flex-col gap-1 border-b border-glass-border px-6 py-5">
            <h3 className="type-label m-0 tracking-[0.14em]">
              {t("preferences.account")}
            </h3>
            <p className="type-body m-0 text-ice">
              {account?.display_name || account?.email || "—"}
            </p>
            {account?.display_name && account.email && (
              <p className="type-body-s m-0 font-mono text-text-3">
                {account.email}
              </p>
            )}
            <p className="type-body-s m-0 text-text-3">{t("preferences.hint")}</p>
          </section>

          <section className="flex flex-col gap-3 border-b border-glass-border px-6 py-5">
            <div className="flex flex-col gap-1">
              <h3 className="type-label m-0 tracking-[0.14em]">
                {t("preferences.microphone")}
              </h3>
              <p className="type-body-s m-0 text-text-3">
                {t("preferences.microphoneHint")}
              </p>
            </div>
            <MicDiagnostics />
          </section>

          <details className="border-b border-glass-border">
            <summary className="cursor-pointer list-none px-6 py-4 type-label text-text-2 outline-none marker:content-none [&::-webkit-details-marker]:hidden">
              <span className="flex items-center justify-between gap-3">
                <span>{t("preferences.diagnostics")}</span>
                <StatusChip
                  tone={connection === "connected" ? "expected" : "neutral"}
                >
                  {connection === "connected" ? "Connected" : "Unavailable"}
                </StatusChip>
              </span>
              <span className="mt-1.5 block type-body-s font-normal normal-case tracking-normal text-text-3">
                {t("preferences.diagnosticsHint")}
              </span>
            </summary>

            <div className="border-t border-glass-border px-6 py-5">
              {health.isPending ? (
                <LoadingState label="Reading backend health" rows={3} />
              ) : health.isError ? (
                <ErrorState
                  title="Backend health unavailable"
                  message={
                    /failed to fetch/i.test(describeError(health.error))
                      ? "The backend is not reachable from this browser."
                      : describeError(health.error)
                  }
                  onRetry={() => void health.refetch()}
                />
              ) : (
                <div className="flex flex-col gap-5">
                  <KeyValueList>
                    <KeyValue label="Provider" value={health.data.llm_provider} />
                    <KeyValue label="Model" value={health.data.llm_model} mono />
                    <KeyValue label="Environment" value={health.data.app_env} />
                    <KeyValue
                      label="API version"
                      value={health.data.version}
                      mono
                    />
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
                    <KeyValue
                      label="Indexed sources"
                      value={knowledgeUnavailable ? null : availableSources}
                      mono
                    />
                    <KeyValue
                      label="Total documents"
                      value={
                        knowledgeUnavailable
                          ? null
                          : (documents.data?.length ?? null)
                      }
                      mono
                    />
                    <KeyValue
                      label="Frontend mode"
                      value={import.meta.env.MODE}
                    />
                    <KeyValue
                      label="API base"
                      value={API_BASE || "same origin"}
                      mono
                    />
                    <KeyValue
                      label="Speech to text"
                      value={
                        providers.data
                          ? `${providers.data.stt.provider}/${providers.data.stt.model}`
                          : null
                      }
                      mono
                    />
                    <KeyValue
                      label="Text to speech"
                      value={
                        providers.data
                          ? `${providers.data.tts.provider}/${providers.data.tts.model}`
                          : null
                      }
                      mono
                    />
                    <KeyValue
                      label="Ready"
                      value={ready.data?.status ?? null}
                    />
                    <KeyValue label="P50 response latency" value={null} mono />
                    <KeyValue label="P95 response latency" value={null} mono />
                    <KeyValue
                      label="Estimated cost per call"
                      value={null}
                      mono
                    />
                  </KeyValueList>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-fit"
                    onClick={() => {
                      void health.refetch();
                      void documents.refetch();
                      void ready.refetch();
                      void providers.refetch();
                    }}
                  >
                    Refresh
                  </Button>
                </div>
              )}
            </div>
          </details>

          <section className="flex flex-col gap-3 px-6 py-5">
            <div className="flex flex-col gap-1">
              <h3 className="type-label m-0 tracking-[0.14em]">
                {t("preferences.sessionActions")}
              </h3>
              <p className="type-body-s m-0 text-text-3">
                {t("preferences.sessionActionsHint")}
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
              <Button
                variant="destructive"
                size="md"
                disabled={busy}
                icon={<Trash2 aria-hidden size={16} strokeWidth={1.6} />}
                onClick={() => setConfirmDelete(true)}
                className="w-full sm:w-fit"
              >
                {t("account.deleteAccount")}
              </Button>
              <Button
                variant="secondary"
                size="md"
                loading={isSigningOut}
                disabled={busy}
                icon={<LogOut aria-hidden size={16} strokeWidth={1.6} />}
                onClick={() => {
                  void signOut().then(() => navigate("/", { replace: true }));
                }}
                className="w-full sm:w-fit"
              >
                {isSigningOut ? t("account.signingOut") : t("account.signOut")}
              </Button>
            </div>
          </section>
        </GlassPanel>
      </div>

      <Dialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title={t("account.deleteAccountTitle")}
        description={t("account.deleteAccountBody")}
        footer={
          <>
            <Button
              variant="ghost"
              size="md"
              disabled={isDeletingAccount}
              onClick={() => setConfirmDelete(false)}
            >
              {tCommon("actions.cancel")}
            </Button>
            <Button
              variant="destructive"
              size="md"
              loading={isDeletingAccount}
              onClick={() => {
                void deleteAccount().then(() => {
                  setConfirmDelete(false);
                  navigate("/", { replace: true });
                });
              }}
            >
              {isDeletingAccount
                ? t("account.deletingAccount")
                : t("account.deleteAccountConfirm")}
            </Button>
          </>
        }
      />
    </WorkspaceSplit>
  );
}
