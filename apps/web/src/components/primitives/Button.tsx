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
  /** Soft hover glow (call CTAs). */
  glow?: boolean;
};

const base =
  "inline-flex select-none items-center justify-center gap-2 rounded-sm border font-medium " +
  "transition-[background-color,border-color,color,transform,box-shadow] duration-[var(--motion-fast)] " +
  "ease-[var(--motion-ease)] active:scale-[0.99] disabled:pointer-events-none disabled:opacity-45";

const variants: Record<ButtonVariant, string> = {
  inverse:
    "border-action-glass-border bg-action-glass font-semibold text-ice " +
    "shadow-[inset_0_1px_0_rgba(255,255,255,0.14)] backdrop-blur-[18px] " +
    "[&_*]:text-ice hover:border-action-glass-border hover:bg-action-glass-hover",
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

const glowByVariant: Partial<Record<ButtonVariant, string>> = {
  primary:
    "hover:shadow-[0_0_0_1px_color-mix(in_oklab,var(--limen-action)_35%,transparent),0_0_28px_color-mix(in_oklab,var(--limen-action)_42%,transparent)]",
  inverse:
    "hover:shadow-[0_0_0_1px_color-mix(in_oklab,var(--limen-action)_35%,transparent),0_0_28px_color-mix(in_oklab,var(--limen-action)_42%,transparent)]",
  secondary:
    "hover:shadow-[0_0_0_1px_color-mix(in_oklab,var(--limen-action)_28%,transparent),0_0_24px_color-mix(in_oklab,var(--limen-action)_32%,transparent)]",
  destructive:
    "hover:shadow-[0_0_0_1px_color-mix(in_oklab,var(--limen-coral)_40%,transparent),0_0_28px_color-mix(in_oklab,var(--limen-coral)_38%,transparent)]",
};

const sizes: Record<ButtonSize, string> = {
  sm: "h-9 px-3 type-body-s",
  md: "h-11 px-4 type-body",
  lg: "h-12 px-6 type-body",
};

export function Button({
  variant = "secondary",
  size = "md",
  asChild = false,
  loading = false,
  icon,
  glow = false,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  const Component = asChild ? Slot : "button";

  return (
    <Component
      className={cn(
        base,
        variants[variant],
        sizes[size],
        glow ? glowByVariant[variant] : null,
        className,
      )}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? (
        <LoaderCircle aria-hidden size={16} className="animate-spin" />
      ) : (
        icon
      )}
      <Slottable>{children}</Slottable>
    </Component>
  );
}
