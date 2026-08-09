import { useTranslation } from "react-i18next";
import { Outlet, useLocation, useMatches } from "react-router-dom";

import { ConnectionState } from "../../components/feedback/ConnectionState";
import { AccountMenu } from "../../components/shell/AccountMenu";
import { AppShell } from "../../components/shell/AppShell";
import { ContextHeader } from "../../components/shell/ContextHeader";
import {
  healthConnectionStatus,
  useHealth,
} from "../../features/diagnostics/useHealth";
import type { RouteMeta } from "../router/routeMeta";

/** Workspace chrome. API health detail stays quiet except on Settings. */
export function WorkspaceLayout() {
  const matches = useMatches();
  const location = useLocation();
  const health = useHealth();
  const { t } = useTranslation("shell");

  const meta = [...matches]
    .reverse()
    .map((match) => match.handle as RouteMeta | undefined)
    .find((handle): handle is RouteMeta => Boolean(handle?.titleKey));

  const onSettings = location.pathname.startsWith("/settings");
  const status = healthConnectionStatus(health);
  const detail =
    onSettings && health.data
      ? `API v${health.data.version}`
      : onSettings && status === "disconnected"
        ? "API unreachable"
        : undefined;

  return (
    <AppShell
      header={
        <ContextHeader
          title={t(meta?.titleKey ?? "routes.fallback.title")}
          subtitle={meta?.subtitleKey ? t(meta.subtitleKey) : undefined}
          status={
            onSettings ? (
              <ConnectionState status={status} detail={detail} />
            ) : undefined
          }
          actions={<AccountMenu />}
        />
      }
    >
      <Outlet />
    </AppShell>
  );
}
