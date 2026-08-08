import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/cn";

type PanelProps = HTMLAttributes<HTMLDivElement> & {
  /** Rendered above the content with a hairline separator. */
  title?: ReactNode;
  actions?: ReactNode;
  /** Body scrolls instead of growing the panel. */
  scroll?: boolean;
  padded?: boolean;
};

function PanelFrame({
  className,
  title,
  actions,
  children,
  scroll = false,
  padded = true,
  ...rest
}: PanelProps) {
  return (
    <section className={cn("relative flex min-h-0 flex-col", className)} {...rest}>
      {(title || actions) && (
        <header className="relative z-[1] flex min-h-14 shrink-0 items-center justify-between gap-4 border-b border-glass-border px-6 py-3.5">
          {typeof title === "string" ? (
            <h2 className="type-label m-0 tracking-[0.14em]">{title}</h2>
          ) : (
            title
          )}
          {actions && (
            <div className="flex shrink-0 items-center gap-2">{actions}</div>
          )}
        </header>
      )}
      <div
        className={cn(
          "relative z-[1] min-h-0 flex-1",
          padded && "px-6 py-5",
          scroll && "limen-scroll",
        )}
      >
        {children}
      </div>
    </section>
  );
}

/** Level 1 — soft glass. Cards and secondary panels. */
export function GlassPanel(props: PanelProps) {
  return (
    <PanelFrame
      {...props}
      className={cn("glass-1 sheen-top rounded-lg", props.className)}
    />
  );
}

/** Level 0 — solid. Dense tables, transcripts, long-form text. */
export function SolidPanel(props: PanelProps) {
  return (
    <PanelFrame
      {...props}
      className={cn("glass-0 rounded-lg", props.className)}
    />
  );
}

/** Level 2 — inspector glass. Side panes and contextual detail. */
export function InspectorPanel(props: PanelProps) {
  return (
    <PanelFrame
      {...props}
      className={cn("glass-2 sheen-top rounded-lg", props.className)}
    />
  );
}
