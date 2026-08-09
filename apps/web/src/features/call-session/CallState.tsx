import type { CallPhase } from "../../api/types";
import { cn } from "../../lib/cn";
import { useTranslation } from "react-i18next";
import { phasePresentation } from "./callPhase";

/** Phase announcement. Labels come from i18n; accent tokens stay in callPhase. */
export function CallState({
  phase,
  className,
}: {
  phase: CallPhase;
  className?: string;
}) {
  const { t } = useTranslation("call");
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
        {t(`phases.${phase}.label`)}
      </p>
      <p className="type-body-l m-0 max-w-[36ch] text-balance text-ice">
        {t(`phases.${phase}.description`)}
      </p>
    </div>
  );
}
