import * as RadixSelect from "@radix-ui/react-select";
import { CircleCheck } from "lucide-react";
import { useId } from "react";

import { cn } from "../../lib/cn";

export type SelectOption = {
  value: string;
  label: string;
  disabled?: boolean;
};

type SelectProps = {
  label: string;
  value: string;
  options: SelectOption[];
  onValueChange: (value: string) => void;
  disabled?: boolean;
  hint?: string;
  className?: string;
};

export function Select({
  label,
  value,
  options,
  onValueChange,
  disabled,
  hint,
  className,
}: SelectProps) {
  const id = useId();

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="type-label">
        {label}
      </label>
      <RadixSelect.Root
        value={value}
        onValueChange={onValueChange}
        disabled={disabled}
      >
        <RadixSelect.Trigger
          id={id}
          className={cn(
            "flex h-11 items-center justify-between gap-2 rounded-sm border border-glass-border",
            "bg-[color-mix(in_oklab,var(--limen-bg-0)_70%,transparent)] px-3 text-left text-ice",
            "data-[disabled]:opacity-45",
            "focus:border-[color-mix(in_oklab,var(--limen-cyan)_55%,transparent)]",
          )}
        >
          <RadixSelect.Value />
          <RadixSelect.Icon className="text-text-3">▾</RadixSelect.Icon>
        </RadixSelect.Trigger>
        <RadixSelect.Portal>
          <RadixSelect.Content
            position="popper"
            sideOffset={6}
            className="glass-2 motion-fade z-50 min-w-[12rem] overflow-hidden rounded-sm p-1"
          >
            <RadixSelect.Viewport>
              {options.map((option) => (
                <RadixSelect.Item
                  key={option.value}
                  value={option.value}
                  disabled={option.disabled}
                  className={cn(
                    "flex cursor-default items-center justify-between gap-3 rounded-xs px-3 py-2",
                    "text-[0.9375rem] text-text-2 outline-none",
                    "data-[highlighted]:bg-[var(--glass-highlight)] data-[highlighted]:text-ice",
                    "data-[state=checked]:text-cyan data-[disabled]:opacity-40",
                  )}
                >
                  <RadixSelect.ItemText>{option.label}</RadixSelect.ItemText>
                  <RadixSelect.ItemIndicator>
                    <CircleCheck aria-hidden size={14} />
                  </RadixSelect.ItemIndicator>
                </RadixSelect.Item>
              ))}
            </RadixSelect.Viewport>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>
      {hint && <p className="type-body-s m-0 text-text-3">{hint}</p>}
    </div>
  );
}
