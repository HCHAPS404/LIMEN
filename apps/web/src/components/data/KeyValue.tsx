import type { ReactNode } from "react";

import { cn } from "../../lib/cn";

type KeyValueProps = {
  label: string;
  value: ReactNode | null | undefined;
  mono?: boolean;
  className?: string;
};

export function KeyValue({ label, value, mono, className }: KeyValueProps) {
  const empty = value === null || value === undefined || value === "";

  return (
    <div
      className={cn(
        "grid grid-cols-[minmax(7rem,0.42fr)_minmax(0,1fr)] items-baseline gap-x-6 gap-y-1",
        "border-b border-glass-border py-3.5 last:border-b-0",
        className,
      )}
    >
      <dt className="type-label m-0 shrink-0 self-center">{label}</dt>
      <dd
        className={cn(
          "m-0 min-w-0 text-right break-words",
          empty ? "text-[0.9375rem] text-text-3" : "text-[0.9375rem] text-ice",
          mono && "type-metric tabular text-[0.875rem]",
        )}
      >
        {empty ? "Unknown" : value}
      </dd>
    </div>
  );
}

export function KeyValueList({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <dl className={cn("m-0 flex flex-col", className)}>{children}</dl>;
}
