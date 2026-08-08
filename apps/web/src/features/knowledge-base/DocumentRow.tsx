import { FileText } from "lucide-react";

import type { KnowledgeDocument } from "../../api/types";
import { formatBytes, formatTimestamp } from "../../lib/format";
import { cn } from "../../lib/cn";
import { DocumentStatus } from "./DocumentStatus";

export function DocumentRow({
  document,
  selected,
  onSelect,
}: {
  document: KnowledgeDocument;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected || undefined}
      className={cn(
        "flex w-full items-center gap-3 rounded-xs px-3 py-3 text-left",
        "transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
        selected
          ? "bg-[color-mix(in_oklab,var(--limen-cyan)_9%,transparent)]"
          : "hover:bg-[var(--glass-highlight)]",
      )}
    >
      <FileText
        aria-hidden
        size={16}
        strokeWidth={1.5}
        className="shrink-0 text-text-3"
      />
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="type-body truncate text-ice">
          {document.source_name}
        </span>
        <span className="type-body-s tabular text-text-3">
          v{document.version} · {formatTimestamp(document.uploaded_at)}
          {document.size_bytes ? ` · ${formatBytes(document.size_bytes)}` : ""}
        </span>
      </span>
      <DocumentStatus status={document.status} />
    </button>
  );
}
