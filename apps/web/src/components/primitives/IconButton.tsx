import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/cn";

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  /** Required: icon-only controls must expose an accessible name. */
  label: string;
  icon: ReactNode;
  tone?: "neutral" | "primary" | "destructive";
};

const tones = {
  neutral: "text-text-2 hover:text-ice hover:bg-[var(--glass-highlight)]",
  primary:
    "text-cyan hover:bg-[color-mix(in_oklab,var(--limen-cyan)_16%,transparent)]",
  destructive:
    "text-coral hover:bg-[color-mix(in_oklab,var(--limen-coral)_18%,transparent)]",
} as const;

export function IconButton({
  label,
  icon,
  tone = "neutral",
  className,
  ...rest
}: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-sm border border-transparent",
        "transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
        "disabled:pointer-events-none disabled:opacity-40",
        tones[tone],
        className,
      )}
      {...rest}
    >
      {icon}
    </button>
  );
}
