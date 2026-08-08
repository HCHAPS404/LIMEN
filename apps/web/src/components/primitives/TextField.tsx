import { useId, type InputHTMLAttributes, type ReactNode } from "react";

import { cn } from "../../lib/cn";

type TextFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  /** Always rendered; a placeholder is not a label. */
  label: string;
  hint?: ReactNode;
  error?: string;
};

export function TextField({
  label,
  hint,
  error,
  className,
  ...rest
}: TextFieldProps) {
  const id = useId();
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="type-label">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          "h-11 w-full rounded-sm border bg-[color-mix(in_oklab,var(--limen-bg-0)_70%,transparent)]",
          "px-3 text-ice placeholder:text-text-3",
          "transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
          error
            ? "border-[color-mix(in_oklab,var(--limen-coral)_55%,transparent)]"
            : "border-glass-border focus:border-[color-mix(in_oklab,var(--limen-cyan)_55%,transparent)]",
          className,
        )}
        {...rest}
      />
      {error ? (
        <p id={`${id}-error`} className="type-body-s m-0 text-coral">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="type-body-s m-0 text-text-3">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
