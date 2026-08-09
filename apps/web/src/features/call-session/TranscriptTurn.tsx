import type { TranscriptTurnRecord } from "../../api/types";
import { StatusChip } from "../../components/data/StatusChip";
import { formatClockTime } from "../../lib/format";
import { cn } from "../../lib/cn";

export function TranscriptTurn({ turn }: { turn: TranscriptTurnRecord }) {
  const isPatient = turn.speaker === "patient";

  return (
    <article
      className={cn(
        "motion-fade flex flex-col gap-1.5 border-l-2 py-2 pl-3",
        isPatient
          ? "border-l-[color-mix(in_oklab,var(--limen-cyan)_50%,transparent)]"
          : "border-l-[color-mix(in_oklab,var(--limen-teal)_50%,transparent)]",
      )}
    >
      <header className="flex items-center gap-2">
        <span className="type-label m-0">
          {isPatient ? "Patient" : "LIMEN"}
        </span>
        <span className="type-body-s tabular text-text-3">
          {formatClockTime(turn.timestamp)}
        </span>
        {turn.interrupted && (
          <StatusChip tone="review">Interrupted</StatusChip>
        )}
      </header>
      {/* Patient speech is untrusted input: rendered as text, never as markup. */}
      <p className="type-body-l m-0 text-ice">{turn.text}</p>
    </article>
  );
}
