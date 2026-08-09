import { ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { CallSummary } from "../../api/types";
import { RiskBadge } from "../../components/data/RiskBadge";
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
                className="type-label border-b border-[color-mix(in_oklab,var(--glass-border)_55%,transparent)] px-4 py-3 whitespace-nowrap"
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
              className="border-b border-[color-mix(in_oklab,var(--glass-border)_40%,transparent)] align-middle transition-colors duration-[var(--motion-fast)] last:border-b-0 hover:bg-[var(--glass-highlight)]"
            >
              <td className="type-body-s max-w-[8rem] truncate tabular px-4 py-4 text-text-2">
                {call.call_id.slice(0, 8)}
              </td>
              <td className="type-body px-4 py-4 text-ice">
                {call.patient_alias}
              </td>
              <td className="type-body-s px-4 py-4 text-text-2">
                {call.procedure ?? t("unknown")}
              </td>
              <td className="type-body-s tabular px-4 py-4 text-text-2">
                {call.postoperative_day ?? "—"}
              </td>
              <td className="type-body-s px-4 py-4 text-text-2">
                {formatTimestamp(call.started_at)}
              </td>
              <td className="px-4 py-4">
                <RiskBadge risk={call.final_risk} size="sm" />
              </td>
              <td className="px-4 py-4">
                {call.escalated ? (
                  <span className="type-body-s font-medium text-coral">
                    {t("yes")}
                  </span>
                ) : (
                  <span className="type-body-s text-text-3">{t("no")}</span>
                )}
              </td>
              <td className="type-body-s tabular px-4 py-4 text-text-2">
                {call.duration_seconds !== null &&
                call.duration_seconds !== undefined
                  ? formatDuration(call.duration_seconds)
                  : "—"}
              </td>
              <td className="px-4 py-4 text-right">
                <Link
                  to={`/trace/${call.call_id}`}
                  className="type-body-s inline-flex items-center gap-1 text-violet"
                >
                  {t("openTrace")}
                  <ChevronRight aria-hidden size={14} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
