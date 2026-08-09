import { useId } from "react";

import { cn } from "../../lib/cn";

/** The threshold mark: a four-point star held inside the liminal line. */
export function LimenMark({
  size = 24,
  className,
}: {
  size?: number;
  className?: string;
}) {
  const gradientId = useId();

  return (
    <svg
      viewBox="0 0 32 32"
      width={size}
      height={size}
      aria-hidden
      className={cn("shrink-0", className)}
    >
      <defs>
        <linearGradient id={gradientId} x1="16" y1="2" x2="16" y2="30">
          <stop offset="0%" stopColor="var(--limen-beam)" />
          <stop offset="100%" stopColor="var(--limen-cyan)" />
        </linearGradient>
      </defs>
      <path
        d="M16 2c1.1 6.6 5.4 10.9 12 12-6.6 1.1-10.9 5.4-12 12-1.1-6.6-5.4-10.9-12-12C10.6 12.9 14.9 8.6 16 2Z"
        fill={`url(#${gradientId})`}
      />
      <path
        d="M2.5 16h27"
        stroke="var(--limen-teal)"
        strokeWidth="1"
        strokeLinecap="round"
        opacity="0.55"
      />
    </svg>
  );
}

export function LimenWordmark({
  size = "md",
  className,
}: {
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
}) {
  const scale = {
    sm: "text-[0.875rem] tracking-[0.3em]",
    md: "text-[1.0625rem] tracking-[0.32em]",
    lg: "text-[1.625rem] tracking-[0.36em]",
    xl: "text-[clamp(3.25rem,10vw,7.5rem)] tracking-[0.16em]",
  }[size];

  return (
    <span
      className={cn(
        "font-semibold text-white-ice uppercase select-none",
        scale,
        className,
      )}
    >
      Limen
    </span>
  );
}

export function LimenLockup({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LimenMark size={16} />
      <LimenWordmark size="sm" className="tracking-[0.28em]" />
    </span>
  );
}
