import type { TraceStage } from "../../api/types";

/** Violet is reserved for audit semantics; evidence stays teal and risk keeps the
 *  clinical palette (FRONTEND.md section 18). */
export const traceStageView: Record<TraceStage, { label: string; accent: string }> =
  {
    "call.started": {
      label: "Call started",
      accent: "var(--limen-text-2)",
    },
    patient_statement: {
      label: "Patient statement",
      accent: "var(--limen-cyan)",
    },
    clinical_extraction: {
      label: "Clinical extraction",
      accent: "var(--limen-violet)",
    },
    uncertainty: {
      label: "Uncertainty",
      accent: "var(--limen-amber)",
    },
    retrieval: { label: "Retrieval", accent: "var(--limen-teal)" },
    safety_evaluation: {
      label: "Safety evaluation",
      accent: "var(--limen-amber)",
    },
    response: { label: "Response", accent: "var(--limen-violet)" },
    escalation: { label: "Escalation", accent: "var(--limen-coral)" },
    session_end: { label: "Session end", accent: "var(--limen-text-2)" },
    "provider.error": {
      label: "Provider error",
      accent: "var(--limen-coral)",
    },
  };

export function resolveTraceStageView(stage: string): {
  label: string;
  accent: string;
} {
  if (stage in traceStageView) {
    return traceStageView[stage as TraceStage];
  }
  return { label: stage, accent: "var(--limen-text-2)" };
}
