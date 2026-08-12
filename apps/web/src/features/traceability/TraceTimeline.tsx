import { useTranslation } from "react-i18next";

import type { TraceEventRecord } from "../../api/types";
import { RiskBadge } from "../../components/data/RiskBadge";
import { formatClockTime } from "../../lib/format";
import { cn } from "../../lib/cn";
import {
  eventTypeKey,
  resolveEventType,
  resolveTraceAccent,
  resolveTraceCategoryKey,
} from "./eventPresentation";

export function TraceTimeline({
  events,
  selectedId,
  onSelect,
}: {
  events: TraceEventRecord[];
  selectedId: string | null;
  onSelect: (event: TraceEventRecord) => void;
}) {
  const { t } = useTranslation("trace");

  return (
    <ol className="m-0 flex list-none flex-col p-0">
      {events.map((event, index) => {
        const accent = resolveTraceAccent(event);
        const category = String(
          t(`categories.${resolveTraceCategoryKey(event)}` as never, {
            defaultValue: t("categories.step"),
          }),
        );
        const title = String(
          t(`events.${eventTypeKey(resolveEventType(event))}.title` as never, {
            defaultValue: t("events.unknown.title"),
          }),
        );
        const selected = event.event_id === selectedId;
        const last = index === events.length - 1;

        return (
          <li key={event.event_id} className="relative flex gap-3">
            <div className="flex w-4 shrink-0 flex-col items-center pt-3.5">
              <span
                aria-hidden
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ background: accent }}
              />
              {!last && (
                <span
                  aria-hidden
                  className="w-px flex-1 bg-[var(--glass-border)]"
                />
              )}
            </div>

            <button
              type="button"
              onClick={() => onSelect(event)}
              aria-current={selected || undefined}
              className={cn(
                "relative mb-1.5 flex flex-1 flex-col gap-1 rounded-sm px-3 py-3 text-left",
                "transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
                selected
                  ? "bg-[color-mix(in_oklab,var(--limen-violet)_10%,transparent)]"
                  : "hover:bg-[var(--glass-highlight)]",
              )}
            >
              {selected && (
                <span
                  aria-hidden
                  className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-violet"
                />
              )}
              <span className="flex flex-wrap items-center gap-2">
                <span className="type-label m-0" style={{ color: accent }}>
                  {category}
                </span>
                <span className="type-body-s tabular text-text-3">
                  #{event.sequence} · {formatClockTime(event.timestamp)}
                </span>
                {event.risk && <RiskBadge risk={event.risk} size="sm" />}
              </span>
              <span className="type-body text-ice">{title}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
