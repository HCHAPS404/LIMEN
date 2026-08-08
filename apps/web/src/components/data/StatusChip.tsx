import type { ReactNode } from "react";

import { cn } from "../../lib/cn";

export type ChipTone =
  | "neutral"
  | "intelligence"
  | "evidence"
  | "audit"
  | "expected"
  | "review"
  | "escalation";

const tones: Record<ChipTone, string> = {
  neutral:
    "border-glass-border bg-[var(--glass-highlight)] text-text-2",
  intelligence:
    "border-[color-mix(in_oklab,var(--limen-cyan)_40%,transparent)] bg-[color-mix(in_oklab,var(--limen-cyan)_14%,transparent)] text-cyan",
  evidence:
    "border-[color-mix(in_oklab,var(--limen-teal)_45%,transparent)] bg-[color-mix(in_oklab,var(--limen-teal)_16%,transparent)] text-[color-mix(in_oklab,var(--limen-teal)_70%,var(--limen-ice))]",
  audit:
    "border-[color-mix(in_oklab,var(--limen-violet)_42%,transparent)] bg-[color-mix(in_oklab,var(--limen-violet)_14%,transparent)] text-violet",
  expected:
    "border-[color-mix(in_oklab,var(--limen-green)_40%,transparent)] bg-[color-mix(in_oklab,var(--limen-green)_14%,transparent)] text-green",
  review:
    "border-[color-mix(in_oklab,var(--limen-amber)_42%,transparent)] bg-[color-mix(in_oklab,var(--limen-amber)_14%,transparent)] text-amber",
  escalation:
    "border-[color-mix(in_oklab,var(--limen-coral)_45%,transparent)] bg-[color-mix(in_oklab,var(--limen-coral)_15%,transparent)] text-coral",
};

type StatusChipProps = {
  children: ReactNode;
  tone?: ChipTone;
  icon?: ReactNode;
  className?: string;
  title?: string;
};

export function StatusChip({
  children,
  tone = "neutral",
  icon,
  className,
  title,
}: StatusChipProps) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-xs border px-2 py-[0.1875rem]",
        "text-[0.6875rem] leading-[1.4] font-medium tracking-[0.1em] uppercase",
        tones[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}
