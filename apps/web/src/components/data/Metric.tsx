import type { ReactNode } from "react";

import { cn } from "../../lib/cn";

type MetricProps = {
  label: string;
  /** `null` renders the honest empty placeholder. */
  value: ReactNode | null;
  unit?: string;
  hint?: string;
  /** Copy when value is absent (pass through i18n). */
  emptyHint?: string;
  tone?: "default" | "intelligence" | "evidence" | "audit";
  className?: string;
};

const tones = {
  default: "text-white-ice",
  intelligence: "text-cyan",
  evidence: "text-[color-mix(in_oklab,var(--limen-teal)_70%,var(--limen-ice))]",
  audit: "text-violet",
} as const;

export function Metric({
  label,
  value,
  unit,
  hint,
  emptyHint = "Not measured",
  tone = "default",
  className,
}: MetricProps) {
  const measured = value !== null && value !== undefined && value !== "";

  return (
    <div className={cn("flex min-w-0 flex-col gap-1", className)}>
      <span className="type-label">{label}</span>
      <span
        className={cn(
          "type-metric flex items-baseline gap-1 text-[1.375rem] leading-none",
          measured ? tones[tone] : "text-text-3",
        )}
      >
        {measured ? value : "—"}
        {measured && unit && (
          <span className="text-[0.75rem] font-medium text-text-3">{unit}</span>
        )}
      </span>
      <span className="type-body-s text-text-3">
        {measured ? hint : emptyHint}
      </span>
    </div>
  );
}

export function MetricStrip({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 xl:grid-cols-4",
        className,
      )}
    >
      {children}
    </div>
  );
}
