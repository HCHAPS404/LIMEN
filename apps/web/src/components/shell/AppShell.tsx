import type { ReactNode } from "react";

import { useIsMobile } from "../../hooks/useMediaQuery";
import { cn } from "../../lib/cn";
import { NavBarMobile, NavRail } from "./NavRail";

/** Full-viewport application shell: header, rail, workspace.
 *  Operational screens are never constrained by a centered dashboard cage.
 *  Only one navigation variant is mounted, so the rail and the mobile bar never
 *  produce duplicate links in the accessibility tree. */
export function AppShell({
  header,
  children,
}: {
  header: ReactNode;
  children: ReactNode;
}) {
  const isMobile = useIsMobile();

  return (
    <div className="flex h-dvh min-h-0 flex-col overflow-hidden">
      {header}
      <div className="flex min-h-0 flex-1">
        {!isMobile && <NavRail />}
        <main
          className={cn(
            "atmosphere-soft flex min-h-0 min-w-0 flex-1 flex-col",
            isMobile && "pb-14",
          )}
        >
          {children}
        </main>
      </div>
      {isMobile && <NavBarMobile />}
    </div>
  );
}

/** Workspace + optional inspector column (section 12). Pages pass `inspector`
 *  only on desktop; narrower viewports open the same content in a drawer. */
export function WorkspaceSplit({
  children,
  inspector,
  className,
}: {
  children: ReactNode;
  inspector?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid min-h-0 flex-1 gap-5 p-5 md:gap-6 md:p-7 xl:p-8",
        inspector
          ? "grid-cols-1 xl:grid-cols-[minmax(0,1fr)_var(--inspector-width)]"
          : "grid-cols-1",
        className,
      )}
    >
      <div className="flex min-h-0 min-w-0 flex-col gap-4 md:gap-5">
        {children}
      </div>
      {inspector && (
        <aside className="flex min-h-0 flex-col">{inspector}</aside>
      )}
    </div>
  );
}
