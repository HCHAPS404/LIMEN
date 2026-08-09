import { useTranslation } from "react-i18next";

import type { ClinicalCertainty, ClinicalStateSnapshot } from "../../api/types";
import { StatusChip, type ChipTone } from "../../components/data/StatusChip";
import { EmptyState } from "../../components/feedback/EmptyState";
import { cn } from "../../lib/cn";

const FINDING_KEYS: Record<string, string> = {
  pain: "pain",
  pain_severity: "painSeverity",
  wound: "wound",
  wound_heat: "woundHeat",
  fever: "fever",
  bleeding: "bleeding",
  breathing: "breathing",
  nausea: "nausea",
};

/** Findings carry their certainty explicitly. Absent information stays UNKNOWN;
 *  it is never rendered as normal. */
export function ClinicalStateGrid({
  state,
  className,
}: {
  state: ClinicalStateSnapshot | null;
  className?: string;
}) {
  const { t } = useTranslation("call");

  if (!state || state.findings.length === 0) {
    return (
      <EmptyState
        density="inline"
        title={t("clinical.emptyTitle")}
        description={t("clinical.emptyBody")}
        className={className}
      />
    );
  }

  const certaintyView: Record<
    ClinicalCertainty,
    { label: string; tone: ChipTone }
  > = {
    KNOWN_NORMAL: { label: t("clinical.certainty.knownNormal"), tone: "expected" },
    KNOWN_ABNORMAL: {
      label: t("clinical.certainty.knownAbnormal"),
      tone: "escalation",
    },
    IMPROVING: { label: t("clinical.certainty.improving"), tone: "intelligence" },
    UNKNOWN: { label: t("clinical.certainty.unknown"), tone: "review" },
    CONFLICTING: { label: t("clinical.certainty.conflicting"), tone: "review" },
  };

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {state.findings.map((finding) => {
          const view =
            certaintyView[finding.certainty] ?? certaintyView.UNKNOWN;
          const nameKey = FINDING_KEYS[finding.name];
          const label = nameKey
            ? t(`clinical.findings.${nameKey}` as "clinical.findings.pain")
            : finding.name;
          return (
            <li
              key={finding.name}
              className="flex items-start justify-between gap-3 py-2.5"
            >
              <div className="flex min-w-0 flex-col gap-0.5">
                <span className="type-body text-ice">{label}</span>
                {finding.notes && (
                  <span className="type-body-s text-text-3">
                    {humanizeNotes(finding.notes)}
                  </span>
                )}
              </div>
              <StatusChip tone={view.tone}>{view.label}</StatusChip>
            </li>
          );
        })}
      </ul>

      {state.open_questions.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="type-label">{t("clinical.openQuestions")}</span>
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {state.open_questions.map((question) => (
              <li key={question} className="type-body-s text-amber">
                {question}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Prefer readable peak/current lines over raw English keys in notes. */
function humanizeNotes(notes: string): string {
  return notes
    .replace(/\bpico=/gi, "pico ")
    .replace(/\bactual=/gi, "actual ")
    .replace(/\bcurso=/gi, "curso ")
    .replace(/\bseverity=/gi, "intensidad ")
    .replace(/\bseventy=/gi, "intensidad ");
}
