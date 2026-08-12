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
 * Workspace context bar — page identity left, utilities in a solid side tray.
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
        "relative flex h-[var(--header-height)] shrink-0 items-stretch",
        "border-b border-[color-mix(in_oklab,var(--limen-ice)_28%,transparent)]",
        "bg-[color-mix(in_oklab,var(--limen-bg-2)_42%,transparent)] backdrop-blur-[24px]",
        className,
      )}
    >
      <div className="flex min-w-0 flex-1 items-center gap-3 px-4 md:gap-4 md:px-8">
        {isMobile ? (
          <Link
            to="/"
            aria-label="LIMEN home"
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-[color-mix(in_oklab,var(--limen-ice)_24%,transparent)] bg-[color-mix(in_oklab,var(--limen-bg-1)_50%,transparent)] transition-colors duration-[var(--motion-fast)] hover:border-[color-mix(in_oklab,var(--limen-ice)_36%,transparent)] hover:bg-[color-mix(in_oklab,var(--limen-bg-1)_70%,transparent)]"
          >
            <LimenMark size={18} />
          </Link>
        ) : null}

        <div className="flex min-w-0 flex-1 flex-col justify-center gap-1">
          <h1 className="type-h2 m-0 truncate text-ice">{title}</h1>
          {subtitle ? (
            <p className="type-body-s m-0 hidden max-w-[40rem] truncate text-text-3 sm:block">
              {subtitle}
            </p>
          ) : null}
        </div>
      </div>

      {(status || actions) && (
        <div
          className={cn(
            "flex shrink-0 items-center gap-3 px-3 md:gap-4 md:px-6",
            "border-l border-[color-mix(in_oklab,var(--limen-ice)_28%,transparent)]",
            "bg-[color-mix(in_oklab,var(--limen-bg-1)_48%,transparent)]",
          )}
        >
          {status ? (
            <div className="hidden items-center sm:flex">{status}</div>
          ) : null}
          {actions ? <div className="flex items-center">{actions}</div> : null}
        </div>
      )}
    </header>
  );
}
