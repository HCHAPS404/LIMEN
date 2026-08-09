import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { useIsMobile } from "../../hooks/useMediaQuery";
import { cn } from "../../lib/cn";
import { LimenMark } from "../brand/Logo";

type ContextHeaderProps = {
  title: string;
  subtitle?: ReactNode;
  status?: ReactNode;
  actions?: ReactNode;
  className?: string;
};

/**
 * Workspace context bar — page identity first, chrome second.
 * Brand lives in the rail on desktop; mobile keeps a compact home mark.
 */
export function ContextHeader({
  title,
  subtitle,
  status,
  actions,
  className,
}: ContextHeaderProps) {
  const isMobile = useIsMobile();

  return (
    <header
      className={cn(
        "relative flex h-[var(--header-height)] shrink-0 items-center gap-4 px-5 md:gap-6 md:px-7",
        "bg-[color-mix(in_oklab,var(--limen-bg-1)_22%,transparent)] backdrop-blur-[20px]",
        className,
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,color-mix(in_oklab,var(--limen-ice)_14%,transparent)_20%,color-mix(in_oklab,var(--limen-ice)_14%,transparent)_80%,transparent)]"
      />
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-[linear-gradient(90deg,transparent_4%,color-mix(in_oklab,var(--limen-ice)_11%,transparent)_18%,color-mix(in_oklab,var(--limen-ice)_9%,transparent)_82%,transparent_96%)]"
      />

      {isMobile ? (
        <Link
          to="/"
          aria-label="LIMEN home"
          className="relative z-[1] inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md transition-colors duration-[var(--motion-fast)] hover:bg-[color-mix(in_oklab,var(--limen-ice)_6%,transparent)]"
        >
          <LimenMark size={18} />
        </Link>
      ) : null}

      <div className="relative z-[1] flex min-w-0 flex-1 flex-col justify-center gap-0.5">
        <h1 className="type-h3 m-0 truncate text-ice">{title}</h1>
        {subtitle ? (
          <p className="type-body-s m-0 hidden truncate text-text-3 sm:block">
            {subtitle}
          </p>
        ) : null}
      </div>

      <div className="relative z-[1] ml-auto flex shrink-0 items-center gap-2.5 md:gap-3">
        {status ? (
          <div className="hidden items-center sm:flex">{status}</div>
        ) : null}
        {actions}
      </div>
    </header>
  );
}
