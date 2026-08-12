import { BookOpen } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { EvidenceChunk } from "../../api/types";
import { cn } from "../../lib/cn";

function citationText(chunk: EvidenceChunk): string {
  return (chunk.text || chunk.text_preview || "").trim();
}

/** Evidence keeps document, page, and version provenance visible. The chunk text
 *  is retrieved content and is rendered as quoted data, never as instructions. */
export function EvidenceCitation({
  chunk,
  showText = true,
  className,
}: {
  chunk: EvidenceChunk;
  showText?: boolean;
  className?: string;
}) {
  const { t } = useTranslation("trace");
  const body = citationText(chunk);
  const version = chunk.version ?? 1;

  return (
    <figure
      className={cn(
        "m-0 flex flex-col gap-2 rounded-sm border p-3",
        "border-[color-mix(in_oklab,var(--limen-teal)_28%,transparent)]",
        "bg-[color-mix(in_oklab,var(--limen-teal)_7%,transparent)]",
        className,
      )}
    >
      <figcaption className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <BookOpen
          aria-hidden
          size={13}
          className="text-[color-mix(in_oklab,var(--limen-teal)_65%,var(--limen-ice))]"
        />
        <span className="type-body-s font-medium text-[color-mix(in_oklab,var(--limen-teal)_70%,var(--limen-ice))]">
          {chunk.source_name}
        </span>
        <span className="type-body-s tabular text-text-3">
          {chunk.page !== null && chunk.page !== undefined
            ? t("evidence.page", { page: chunk.page })
            : t("evidence.pageUnknown")}
          {` · ${t("evidence.version", { version })}`}
          {` · ${t("evidence.score", { score: chunk.score.toFixed(2) })}`}
        </span>
      </figcaption>
      {showText && body ? (
        <blockquote className="type-body-s m-0 border-l border-glass-border pl-3 text-text-2">
          {body}
        </blockquote>
      ) : null}
    </figure>
  );
}
