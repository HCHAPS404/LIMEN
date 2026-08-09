import { ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { CallSummary } from "../../api/types";
import { RiskBadge } from "../../components/data/RiskBadge";
import { StatusChip } from "../../components/data/StatusChip";
import { formatDuration, formatTimestamp } from "../../lib/format";

export function SessionsTable({ calls }: { calls: CallSummary[] }) {
  const { t } = useTranslation("sessions");
  const headers = [
    t("headers.call"),
    t("headers.patient"),
    t("headers.procedure"),
    t("headers.pod"),
    t("headers.started"),
    t("headers.risk"),
    t("headers.escalated"),
    t("headers.duration"),
    "",
  ];

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full min-w-[52rem] border-collapse text-left">
        <thead>
          <tr>
            {headers.map((header, index) => (
              <th
                key={header || `spacer-${index}`}
                scope="col"
                className="type-label border-b border-glass-border px-3 py-2.5 whitespace-nowrap"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {calls.map((call) => (
            <tr
              key={call.call_id}
              className="border-b border-glass-border align-middle transition-colors duration-[var(--motion-fast)] last:border-b-0 hover:bg-[var(--glass-highlight)]"
            >
              <td className="type-body-s max-w-[8rem] truncate tabular px-3 py-3 text-text-2">
                {call.call_id.slice(0, 8)}
              </td>
              <td className="type-body px-3 py-3 text-ice">
                {call.patient_alias}
              </td>
              <td className="type-body-s px-3 py-3 text-text-2">
                {call.procedure ?? t("unknown")}
              </td>
              <td className="type-body-s tabular px-3 py-3 text-text-2">
                {call.postoperative_day ?? "—"}
              </td>
              <td className="type-body-s px-3 py-3 text-text-2">
                {formatTimestamp(call.started_at)}
              </td>
              <td className="px-3 py-3">
                <RiskBadge risk={call.final_risk} size="sm" />
              </td>
              <td className="px-3 py-3">
                {call.escalated ? (
                  <StatusChip tone="escalation">{t("yes")}</StatusChip>
                ) : (
                  <StatusChip>{t("no")}</StatusChip>
                )}
              </td>
              <td className="type-body-s tabular px-3 py-3 text-text-2">
                {call.duration_seconds !== null &&
                call.duration_seconds !== undefined
                  ? formatDuration(call.duration_seconds)
                  : "—"}
              </td>
              <td className="px-3 py-3 text-right">
                <div className="flex flex-col items-end gap-1 sm:flex-row sm:justify-end sm:gap-3">
                  <Link
                    to={`/trace/${call.call_id}`}
                    className="type-body-s inline-flex items-center gap-1 text-violet"
                  >
                    {t("openTrace")}
                    <ChevronRight aria-hidden size={14} />
                  </Link>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
