import * as Switch from "@radix-ui/react-switch";
import { useId } from "react";

import { cn } from "../../lib/cn";

type ToggleProps = {
  label: string;
  checked: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  description?: string;
  className?: string;
};

export function Toggle({
  label,
  checked,
  onCheckedChange,
  disabled,
  description,
  className,
}: ToggleProps) {
  const id = useId();

  return (
    <div className={cn("flex items-start justify-between gap-4", className)}>
      <div className="flex flex-col gap-0.5">
        <label htmlFor={id} className="type-body text-ice">
          {label}
        </label>
        {description && (
          <p className="type-body-s m-0 text-text-3">{description}</p>
        )}
      </div>
      <Switch.Root
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
        className={cn(
          "relative h-6 w-11 shrink-0 rounded-full border border-glass-border",
          "bg-[color-mix(in_oklab,var(--limen-bg-0)_70%,transparent)]",
          "transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
          "data-[state=checked]:border-transparent data-[state=checked]:bg-cyan",
          "disabled:opacity-40",
        )}
      >
        <Switch.Thumb
          className={cn(
            "block h-4 w-4 translate-x-1 rounded-full bg-ice",
            "transition-transform duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
            "data-[state=checked]:translate-x-6 data-[state=checked]:bg-bg-0",
          )}
        />
      </Switch.Root>
    </div>
  );
}
