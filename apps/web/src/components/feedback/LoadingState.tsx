import { cn } from "../../lib/cn";

type LoadingStateProps = {
  label: string;
  /** Bars approximate the real layout instead of a generic block. */
  rows?: number;
  className?: string;
};

export function LoadingState({ label, rows = 3, className }: LoadingStateProps) {
  return (
    <div
      className={cn("flex flex-col gap-3", className)}
      aria-busy="true"
      aria-live="polite"
    >
      <p className="type-label m-0">{label}</p>
      {Array.from({ length: rows }, (_, index) => (
        <div
          key={index}
          className="relative h-10 overflow-hidden rounded-sm border border-glass-border bg-[var(--glass-highlight)]"
        >
          <span
            className="absolute inset-y-0 left-0 w-1/4 bg-[linear-gradient(90deg,transparent,color-mix(in_oklab,var(--limen-cyan)_12%,transparent),transparent)]"
            style={{
              animation: `limen-sweep 1.4s var(--motion-ease) ${index * 0.12}s infinite`,
            }}
          />
        </div>
      ))}
    </div>
  );
}
