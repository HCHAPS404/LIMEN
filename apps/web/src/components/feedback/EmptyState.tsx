import type { ReactNode } from "react";

import { cn } from "../../lib/cn";

type EmptyStateProps = {
  /** Short label above the title. Manrope only — operational screens do not
   *  mix in the editorial serif. */
  eyebrow?: string;
  title: string;
  description: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
  /** `stage` centers in a tall workspace; `inline` sits within a panel list. */
  density?: "stage" | "inline";
  className?: string;
};

export function EmptyState({
  eyebrow,
  title,
  description,
  action,
  icon,
  density = "stage",
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "motion-fade flex flex-col text-center",
        density === "inline"
          ? "items-start gap-3 px-1 py-6 text-left"
          : "h-full min-h-[18rem] items-center justify-center gap-5 px-8 py-16",
        className,
      )}
    >
      {icon && <div className="mb-1 text-text-3 opacity-70">{icon}</div>}
      {eyebrow && (
        <p className="type-eyebrow m-0 text-text-3">{eyebrow}</p>
      )}
      <h3
        className={cn(
          "m-0 text-ice",
          density === "inline" ? "type-h3 max-w-[36ch]" : "type-h2 max-w-[28ch]",
        )}
      >
        {title}
      </h3>
      <p
        className={cn(
          "m-0 text-text-2",
          density === "inline"
            ? "type-body max-w-[48ch]"
            : "type-body-l max-w-[42ch]",
        )}
      >
        {description}
      </p>
      {action && <div className={density === "inline" ? "mt-2" : "mt-4"}>{action}</div>}
    </div>
  );
}
