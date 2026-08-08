import { ShieldAlert, ShieldCheck, TriangleAlert } from "lucide-react";
import type { ComponentType } from "react";

import type { RiskLevel } from "../../api/types";

export type RiskPresentation = {
  label: string;
  meaning: string;
  /** Token-derived classes only; risk colors never appear as raw hex. */
  className: string;
  icon: ComponentType<{ size?: number; "aria-hidden"?: boolean }>;
};

/** Risk is never encoded by color alone: each level carries a label and an icon. */
export const riskPresentation: Record<RiskLevel, RiskPresentation> = {
  GREEN: {
    label: "GREEN",
    meaning: "Expected recovery",
    className:
      "border-[color-mix(in_oklab,var(--limen-green)_45%,transparent)] bg-[color-mix(in_oklab,var(--limen-green)_15%,transparent)] text-green",
    icon: ShieldCheck,
  },
  YELLOW: {
    label: "YELLOW",
    meaning: "Uncertain — review",
    className:
      "border-[color-mix(in_oklab,var(--limen-amber)_45%,transparent)] bg-[color-mix(in_oklab,var(--limen-amber)_15%,transparent)] text-amber",
    icon: TriangleAlert,
  },
  ORANGE: {
    label: "ORANGE",
    meaning: "Elevated concern",
    className:
      "border-[color-mix(in_oklab,var(--limen-coral)_38%,var(--limen-amber))] bg-[color-mix(in_oklab,var(--limen-amber)_10%,transparent)] text-[color-mix(in_oklab,var(--limen-amber)_55%,var(--limen-coral))]",
    icon: TriangleAlert,
  },
  RED: {
    label: "RED",
    meaning: "Escalate to clinician",
    className:
      "border-[color-mix(in_oklab,var(--limen-coral)_50%,transparent)] bg-[color-mix(in_oklab,var(--limen-coral)_16%,transparent)] text-coral",
    icon: ShieldAlert,
  },
};

/** Shown when no safety decision exists. Absence is stated, never assumed safe. */
export const unassessedRisk: RiskPresentation = {
  label: "NOT ASSESSED",
  meaning: "No safety decision recorded",
  className: "border-glass-border bg-[var(--glass-highlight)] text-text-2",
  icon: ShieldAlert,
};

export function riskView(risk: RiskLevel | null | undefined): RiskPresentation {
  return risk ? riskPresentation[risk] : unassessedRisk;
}

export function riskMeaning(risk: RiskLevel | null | undefined): string {
  return riskView(risk).meaning;
}
