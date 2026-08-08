import { Slot, Slottable } from "@radix-ui/react-slot";
import { LoaderCircle } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/cn";

export type ButtonVariant =
  | "inverse"
  | "primary"
  | "secondary"
  | "ghost"
  | "destructive";
export type ButtonSize = "sm" | "md" | "lg";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Render as the single child element (router links keep button styling). */
  asChild?: boolean;
  loading?: boolean;
  icon?: ReactNode;
};

const base =
  "inline-flex select-none items-center justify-center gap-2 rounded-sm border font-medium " +
  "transition-[background-color,border-color,color,transform] duration-[var(--motion-fast)] " +
  "ease-[var(--motion-ease)] active:scale-[0.99] disabled:pointer-events-none disabled:opacity-45";

const variants: Record<ButtonVariant, string> = {
  /** Teal glass CTA — brand action tint with blur, not a flat opaque slab. */
  inverse:
    "border-action-glass-border bg-action-glass font-semibold text-ice " +
    "shadow-[inset_0_1px_0_rgba(255,255,255,0.14)] backdrop-blur-[18px] " +
    "[&_*]:text-ice hover:border-action-glass-border hover:bg-action-glass-hover",
  /** Alias kept for existing call sites; same teal glass as inverse. */
  primary:
    "border-action-glass-border bg-action-glass font-semibold text-ice " +
    "shadow-[inset_0_1px_0_rgba(255,255,255,0.14)] backdrop-blur-[18px] " +
    "[&_*]:text-ice hover:border-action-glass-border hover:bg-action-glass-hover",
  secondary:
    "border-glass-border bg-[var(--glass-surface)] text-ice backdrop-blur-[14px] " +
    "hover:border-[var(--glass-border-strong)] hover:bg-[var(--glass-surface-strong)]",
  ghost:
    "border-transparent bg-transparent text-text-2 hover:bg-[var(--glass-highlight)] hover:text-ice",
  destructive:
    "border-[color-mix(in_oklab,var(--limen-coral)_40%,transparent)] " +
    "bg-[color-mix(in_oklab,var(--limen-coral)_13%,transparent)] text-coral " +
    "hover:bg-[color-mix(in_oklab,var(--limen-coral)_22%,transparent)]",
};

const sizes: Record<ButtonSize, string> = {
  sm: "h-9 px-3 text-[0.8125rem]",
  md: "h-11 px-4 text-[0.9375rem]",
  lg: "h-12 px-6 text-[0.9375rem]",
};

export function Button({
  variant = "secondary",
  size = "md",
  asChild = false,
  loading = false,
  icon,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  const Component = asChild ? Slot : "button";

  return (
    <Component
      className={cn(base, variants[variant], sizes[size], className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? (
        <LoaderCircle aria-hidden size={16} className="animate-spin" />
      ) : (
        icon
      )}
      {/* Slottable lets the icon coexist with the slotted child element. */}
      <Slottable>{children}</Slottable>
    </Component>
  );
}
