import type { CallPhase } from "../../api/types";
import { cn } from "../../lib/cn";
import { phasePresentation } from "./callPhase";

/** Phase announcement. `aria-live` keeps screen readers in sync with the voice
 *  flow, and the description carries the meaning so color is never the only cue. */
export function CallState({
  phase,
  className,
}: {
  phase: CallPhase;
  className?: string;
}) {
  const view = phasePresentation[phase];

  return (
    <div
      className={cn("flex flex-col items-center gap-3 text-center", className)}
      aria-live="polite"
      aria-atomic="true"
    >
      <p
        className="type-eyebrow m-0 tracking-[0.18em]"
        style={{ color: view.accent }}
        data-testid="call-phase-label"
      >
        {view.label}
      </p>
      <p className="type-body-l m-0 max-w-[36ch] text-balance text-ice">
        {view.description}
      </p>
    </div>
  );
}
