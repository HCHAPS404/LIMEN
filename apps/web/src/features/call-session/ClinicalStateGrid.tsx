import type { ClinicalCertainty, ClinicalStateSnapshot } from "../../api/types";
import { StatusChip, type ChipTone } from "../../components/data/StatusChip";
import { EmptyState } from "../../components/feedback/EmptyState";
import { cn } from "../../lib/cn";

const certaintyView: Record<
  ClinicalCertainty,
  { label: string; tone: ChipTone }
> = {
  KNOWN_NORMAL: { label: "Known normal", tone: "expected" },
  KNOWN_ABNORMAL: { label: "Known abnormal", tone: "escalation" },
  UNKNOWN: { label: "Unknown", tone: "review" },
  CONFLICTING: { label: "Conflicting", tone: "review" },
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
  if (!state || state.findings.length === 0) {
    return (
      <EmptyState
        title="No clinical state yet"
        description="Findings appear as the patient answers. Nothing is assumed normal before it is reported."
        className={cn("min-h-[8rem]", className)}
      />
    );
  }

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {state.findings.map((finding) => {
          const view = certaintyView[finding.certainty];
          return (
            <li
              key={finding.name}
              className="flex items-start justify-between gap-3 border-b border-glass-border pb-2 last:border-b-0"
            >
              <div className="flex min-w-0 flex-col gap-0.5">
                <span className="type-body text-ice">{finding.name}</span>
                {finding.notes && (
                  <span className="type-body-s text-text-3">{finding.notes}</span>
                )}
              </div>
              <StatusChip tone={view.tone}>{view.label}</StatusChip>
            </li>
          );
        })}
      </ul>

      {state.open_questions.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="type-label">Unresolved questions</span>
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
