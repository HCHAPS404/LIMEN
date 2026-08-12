import type { TFunction } from "i18next";

/** Map Safety Governor reason codes to locale copy under `trace.reasons.*`. */
const EXACT_KEYS = {
  no_rule_triggered: "reasons.noRule",
  state_no_yellow_findings: "reasons.noYellowFindings",
  generative_default: "reasons.generativeDefault",
  Expected_recovery: "reasons.expectedRecovery",
  "Expected recovery": "reasons.expectedRecovery",
} as const;

type ReasonKey = (typeof EXACT_KEYS)[keyof typeof EXACT_KEYS];

export function translateSafetyReason(
  reason: string,
  t: TFunction<"trace">,
): string {
  const exact = EXACT_KEYS[reason as keyof typeof EXACT_KEYS] as
    | ReasonKey
    | undefined;
  if (exact) return t(exact);

  const lower = reason.toLowerCase();
  if (lower === "expected recovery") return t("reasons.expectedRecovery");

  if (reason.startsWith("yellow_pattern:")) {
    if (reason.includes("fiebre")) return t("reasons.yellowFever");
    if (reason.includes("nause")) return t("reasons.yellowNausea");
    return t("reasons.yellowPattern");
  }
  if (reason.startsWith("red_pattern:")) return t("reasons.redPattern");
  if (reason.startsWith("state_finding:")) {
    const body = reason.slice("state_finding:".length).replaceAll(":", " · ");
    return t("reasons.stateFinding", { detail: body });
  }
  if (reason.includes("generative_override_blocked")) {
    return t("reasons.overrideBlocked");
  }

  return reason.replaceAll("_", " ").replaceAll("\\b", "").replaceAll("\\", "");
}
