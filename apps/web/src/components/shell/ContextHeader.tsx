import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { cn } from "../../lib/cn";
import { LimenWordmark } from "../brand/Logo";

type ContextHeaderProps = {
  title: string;
  subtitle?: ReactNode;
  status?: ReactNode;
  actions?: ReactNode;
  className?: string;
};

export function ContextHeader({
  title,
  subtitle,
  status,
  actions,
  className,
}: ContextHeaderProps) {
  return (
    <header
      className={cn(
        "relative flex h-[var(--header-height)] shrink-0 items-center gap-6 border-b border-glass-border px-5 md:px-7",
        "bg-[var(--glass-surface-strong)] backdrop-blur-[32px] saturate-[1.15]",
        className,
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,var(--glass-sheen)_18%,var(--glass-sheen)_82%,transparent)]"
      />

      <Link
        to="/"
        aria-label="LIMEN home"
        className="shrink-0 rounded-xs transition-opacity duration-[var(--motion-fast)] hover:opacity-80"
      >
        <LimenWordmark size="sm" className="tracking-[0.26em]" />
      </Link>

      <span
        aria-hidden
        className="hidden h-8 w-px shrink-0 bg-[var(--glass-border)] sm:block"
      />

      <div className="hidden min-w-0 flex-1 flex-col justify-center gap-1 sm:flex">
        <h1 className="m-0 truncate text-[1rem] font-semibold tracking-[-0.016em] text-ice">
          {title}
        </h1>
        {subtitle && (
          <p className="m-0 truncate text-[0.8125rem] tracking-[-0.006em] text-text-3">
            {subtitle}
          </p>
        )}
      </div>

      <div className="ml-auto flex shrink-0 items-center gap-3">
        {status}
        {actions}
      </div>
    </header>
  );
}
