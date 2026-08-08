import { TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../../lib/cn";
import { Button } from "../primitives/Button";

type ErrorStateProps = {
  title: string;
  /** Must state what failed. Never "Something went wrong." */
  message: ReactNode;
  /** Where in the pipeline the failure happened, when known. */
  stage?: string;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
};

export function ErrorState({
  title,
  message,
  stage,
  onRetry,
  retryLabel = "Retry",
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-start gap-3 rounded-md border p-5",
        "border-[color-mix(in_oklab,var(--limen-coral)_32%,transparent)]",
        "bg-[color-mix(in_oklab,var(--limen-coral)_8%,transparent)]",
        className,
      )}
    >
      <div className="flex items-center gap-2 text-coral">
        <TriangleAlert aria-hidden size={16} />
        <h3 className="type-h3 m-0 text-[1.0625rem]">{title}</h3>
      </div>
      {stage && (
        <p className="type-label m-0">
          Stage <span className="text-text-2">{stage}</span>
        </p>
      )}
      <p className="type-body m-0 max-w-[60ch] text-text-2">{message}</p>
      {onRetry && (
        <Button size="sm" variant="secondary" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
