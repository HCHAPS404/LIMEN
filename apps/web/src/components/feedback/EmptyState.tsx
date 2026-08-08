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
  className?: string;
};

export function EmptyState({
  eyebrow,
  title,
  description,
  action,
  icon,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "motion-fade flex h-full min-h-[18rem] flex-col items-center justify-center gap-5 px-8 py-16 text-center",
        className,
      )}
    >
      {icon && <div className="mb-1 text-text-3 opacity-70">{icon}</div>}
      {eyebrow && (
        <p className="type-eyebrow m-0 text-text-3">{eyebrow}</p>
      )}
      <h3 className="type-h2 m-0 max-w-[28ch] text-ice">{title}</h3>
      <p className="type-body-l m-0 max-w-[42ch] text-text-2">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
