import type { RiskLevel } from "../../api/types";
import { cn } from "../../lib/cn";
import { riskView } from "./riskPresentation";

export type RiskBadgeSize = "sm" | "md" | "lg";

type RiskBadgeProps = {
  risk: RiskLevel | null | undefined;
  size?: RiskBadgeSize;
  /** Renders the plain-language meaning next to the level. */
  showMeaning?: boolean;
  className?: string;
};

const sizes: Record<RiskBadgeSize, string> = {
  sm: "px-2 py-1 type-label gap-1.5",
  md: "px-2.5 py-1.5 type-label gap-2",
  lg: "px-3.5 py-2 type-body-s gap-2.5 !normal-case !tracking-[-0.01em]",
};

const iconSizes: Record<RiskBadgeSize, number> = { sm: 12, md: 14, lg: 18 };

export function RiskBadge({
  risk,
  size = "md",
  showMeaning = false,
  className,
}: RiskBadgeProps) {
  const view = riskView(risk);
  const Icon = view.icon;

  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <span
        className={cn(
          "inline-flex items-center rounded-sm border font-semibold tracking-[0.08em] uppercase",
          view.className,
          sizes[size],
        )}
      >
        <Icon aria-hidden size={iconSizes[size]} />
        {view.label}
      </span>
      {showMeaning && (
        <span className="type-body-s text-text-2">{view.meaning}</span>
      )}
      <span className="sr-only">
        Riesgo clínico {view.label}: {view.meaning}
      </span>
    </span>
  );
}
