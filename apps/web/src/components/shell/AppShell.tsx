import type { ReactNode } from "react";

import { useIsMobile } from "../../hooks/useMediaQuery";
import { cn } from "../../lib/cn";
import { WorkspaceAtmosphere } from "../atmosphere/WorkspaceAtmosphere";
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
    <div className="relative flex h-dvh min-h-0 flex-col overflow-hidden">
      <WorkspaceAtmosphere />

      <div className="relative z-10 flex min-h-0 flex-1 flex-col">
        {header}
        <div className="flex min-h-0 flex-1">
          {!isMobile && <NavRail />}
          <main
            className={cn(
              "flex min-h-0 min-w-0 flex-1 flex-col bg-transparent",
              isMobile && "pb-14",
            )}
          >
            {children}
          </main>
        </div>
      </div>

      {isMobile && <NavBarMobile />}
    </div>
  );
}

/** Workspace + optional inspector column (section 12). Pages pass `inspector`
 *  only on desktop; narrower viewports open the same content in a drawer.
 *
 *  `scroll="panels"` (default) keeps nested panel scroll for dense tables.
 *  `scroll="page"` uses one workspace scrollbar so call/stage layouts are not
 *  clipped into multiple independent panes.
 */
export function WorkspaceSplit({
  children,
  inspector,
  className,
  scroll = "panels",
}: {
  children: ReactNode;
  inspector?: ReactNode;
  className?: string;
  scroll?: "panels" | "page";
}) {
  const pageScroll = scroll === "page";

  return (
    <div
      className={cn(
        "min-h-0 flex-1",
        pageScroll ? "limen-scroll overflow-y-auto" : "flex flex-col",
        className,
      )}
    >
      <div
        className={cn(
          "grid gap-5 p-5 md:gap-6 md:p-7 xl:p-8",
          pageScroll ? "content-start" : "min-h-0 flex-1",
          inspector
            ? "grid-cols-1 xl:grid-cols-[minmax(0,1fr)_var(--inspector-width)]"
            : "grid-cols-1",
        )}
      >
        <div
          className={cn(
            "flex min-w-0 flex-col gap-4 md:gap-5",
            !pageScroll && "min-h-0",
          )}
        >
          {children}
        </div>
        {inspector && (
          <aside
            className={cn("flex flex-col", !pageScroll && "min-h-0")}
          >
            {inspector}
          </aside>
        )}
      </div>
    </div>
  );
}
