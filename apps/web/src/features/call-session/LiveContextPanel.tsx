import { useTranslation } from "react-i18next";

import { EvidenceCitation } from "../../components/data/EvidenceCitation";
import { Metric } from "../../components/data/Metric";
import { RiskBadge } from "../../components/data/RiskBadge";
import { EmptyState } from "../../components/feedback/EmptyState";
import { useCallStore } from "../../state/call-store";
import { ClinicalStateGrid } from "./ClinicalStateGrid";
import { humanizeSafetyReason } from "./safetyReasonEs";

/** Read-only mirror of the live session. Every value comes from the session
 *  event stream; absent data shows as not measured rather than as a default. */
export function LiveContextPanel() {
  const { t } = useTranslation("call");
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
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <span className="type-label">{t("live.safetyDecision")}</span>
        <RiskBadge risk={risk} size="lg" />
        <p className="type-body-s m-0 text-text-2">
          {risk
            ? t(
                (
                  {
                    GREEN: "risk.meaning.green",
                    YELLOW: "risk.meaning.yellow",
                    ORANGE: "risk.meaning.orange",
                    RED: "risk.meaning.red",
                  } as const
                )[risk],
              )
            : t("live.safetyPending")}
        </p>
        {escalated && (
          <p className="type-body-s m-0 font-medium text-coral">
            {t("live.escalated")}
          </p>
        )}
        {reasons.length > 0 && (
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {reasons.map((reason) => (
              <li key={reason} className="type-body-s tabular text-text-2">
                {humanizeSafetyReason(reason)}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 py-2">
        <Metric
          label={t("live.openUnknowns")}
          value={unknowns}
          hint={t("live.openUnknownsHint")}
          tone="intelligence"
        />
        <Metric
          label={t("live.sourcesCited")}
          value={evidence.length > 0 ? evidence.length : null}
          hint={t("live.sourcesCitedHint")}
          tone="evidence"
        />
      </div>

      <div className="flex flex-col gap-2">
        <span className="type-label">{t("live.clinicalState")}</span>
        <ClinicalStateGrid state={clinicalState} />
      </div>

      <div className="flex flex-col gap-2">
        <span className="type-label">{t("live.evidence")}</span>
        {evidence.length === 0 ? (
          <EmptyState
            density="inline"
            title={t("live.noEvidenceTitle")}
            description={t("live.noEvidenceBody")}
          />
        ) : (
          <div className="flex flex-col gap-2">
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
