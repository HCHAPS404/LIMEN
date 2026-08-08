import { EvidenceCitation } from "../../components/data/EvidenceCitation";
import { Metric } from "../../components/data/Metric";
import { RiskBadge } from "../../components/data/RiskBadge";
import { riskMeaning } from "../../components/data/riskPresentation";
import { EmptyState } from "../../components/feedback/EmptyState";
import { useCallStore } from "../../state/call-store";
import { ClinicalStateGrid } from "./ClinicalStateGrid";

/** Read-only mirror of the live session. Every value comes from the session
 *  event stream; absent data shows as not measured rather than as a default. */
export function LiveContextPanel() {
  const risk = useCallStore((state) => state.risk);
  const escalated = useCallStore((state) => state.escalated);
  const reasons = useCallStore((state) => state.safetyReasons);
  const clinicalState = useCallStore((state) => state.clinicalState);
  const evidence = useCallStore((state) => state.evidence);

  const unknowns =
    clinicalState?.findings.filter(
      (finding) =>
        finding.certainty === "UNKNOWN" || finding.certainty === "CONFLICTING",
    ).length ?? null;

  return (
    <div className="flex min-h-0 flex-col gap-5">
      <div className="flex flex-col gap-2">
        <span className="type-label">Safety decision</span>
        <RiskBadge risk={risk} size="lg" />
        <p className="type-body-s m-0 text-text-2">
          {risk ? riskMeaning(risk) : "The Safety Governor has not evaluated a turn yet."}
        </p>
        {escalated && (
          <p className="type-body-s m-0 font-medium text-coral">
            Human escalation requested.
          </p>
        )}
        {reasons.length > 0 && (
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {reasons.map((reason) => (
              <li key={reason} className="type-body-s tabular text-text-2">
                {reason}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 border-y border-glass-border py-4">
        <Metric
          label="Open unknowns"
          value={unknowns}
          hint="Findings without a resolved answer"
          tone="intelligence"
        />
        <Metric
          label="Sources cited"
          value={evidence.length > 0 ? evidence.length : null}
          hint="Distinct evidence chunks this turn"
          tone="evidence"
        />
      </div>

      <div className="flex flex-col gap-2">
        <span className="type-label">Clinical state</span>
        <ClinicalStateGrid state={clinicalState} />
      </div>

      <div className="flex min-h-0 flex-col gap-2">
        <span className="type-label">Evidence</span>
        {evidence.length === 0 ? (
          <EmptyState
            title="No evidence retrieved"
            description="Retrieved chunks appear here with document, page, and version provenance."
            className="min-h-[7rem]"
          />
        ) : (
          <div className="limen-scroll flex min-h-0 flex-col gap-2">
            {evidence.slice(0, 3).map((chunk) => (
              <EvidenceCitation
                key={chunk.chunk_id}
                chunk={chunk}
                showText={false}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
