import { useTranslation } from "react-i18next";
import { Outlet, useMatches } from "react-router-dom";

import { ConnectionState } from "../../components/feedback/ConnectionState";
import { AccountMenu } from "../../components/shell/AccountMenu";
import { AppShell } from "../../components/shell/AppShell";
import { ContextHeader } from "../../components/shell/ContextHeader";
import {
  healthConnectionStatus,
  useHealth,
} from "../../features/diagnostics/useHealth";
import type { RouteMeta } from "../router/routeMeta";

export function WorkspaceLayout() {
  const matches = useMatches();
  const health = useHealth();
  const { t } = useTranslation("shell");

  const meta = [...matches]
    .reverse()
    .map((match) => match.handle as RouteMeta | undefined)
    .find((handle): handle is RouteMeta => Boolean(handle?.titleKey));

  const status = healthConnectionStatus(health);
  const detail = health.data
    ? `API v${health.data.version}`
    : status === "disconnected"
      ? "API unreachable"
      : undefined;

  return (
    <AppShell
      header={
        <ContextHeader
          title={t(meta?.titleKey ?? "routes.fallback.title")}
          subtitle={meta?.subtitleKey ? t(meta.subtitleKey) : undefined}
          status={<ConnectionState status={status} detail={detail} />}
          actions={<AccountMenu />}
        />
      }
    >
      <Outlet />
    </AppShell>
  );
}
