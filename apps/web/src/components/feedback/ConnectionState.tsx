import { useTranslation } from "react-i18next";

import { cn } from "../../lib/cn";

export type ConnectionStatus =
  | "connected"
  | "connecting"
  | "disconnected"
  | "unavailable";

const presentation: Record<
  ConnectionStatus,
  { dot: string; text: string; shell: string }
> = {
  connected: {
    dot: "bg-green",
    text: "text-ice",
    shell: "border-glass-border bg-[var(--glass-highlight)]",
  },
  connecting: {
    dot: "bg-amber motion-breathe",
    text: "text-amber",
    shell:
      "border-[color-mix(in_oklab,var(--limen-amber)_24%,transparent)] bg-[color-mix(in_oklab,var(--limen-amber)_7%,transparent)]",
  },
  disconnected: {
    dot: "bg-coral",
    text: "text-coral",
    shell:
      "border-[color-mix(in_oklab,var(--limen-coral)_24%,transparent)] bg-[color-mix(in_oklab,var(--limen-coral)_7%,transparent)]",
  },
  unavailable: {
    dot: "bg-[var(--limen-text-3)]",
    text: "text-text-3",
    shell: "border-glass-border bg-[var(--glass-highlight)]",
  },
};

type ConnectionStateProps = {
  status: ConnectionStatus;
  detail?: string;
  className?: string;
};

export function ConnectionState({
  status,
  detail,
  className,
}: ConnectionStateProps) {
  const { t } = useTranslation("connection");
  const view = presentation[status];

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2.5 rounded-sm border px-3 py-1.5",
        view.shell,
        className,
      )}
    >
      <span
        aria-hidden
        className={cn("h-1.5 w-1.5 shrink-0 rounded-full", view.dot)}
      />
      <span
        className={cn(
          "text-[0.8125rem] font-medium tracking-[-0.01em]",
          view.text,
        )}
      >
        {t(status)}
      </span>
      {detail && (
        <span className="hidden text-[0.8125rem] text-text-3 sm:inline">
          · {detail}
        </span>
      )}
    </div>
  );
}
