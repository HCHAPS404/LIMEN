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
        "relative flex w-full items-center gap-3 rounded-sm px-3 py-3.5 text-left",
        "transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
        selected
          ? "bg-[color-mix(in_oklab,var(--limen-cyan)_10%,transparent)]"
          : "hover:bg-[var(--glass-highlight)]",
      )}
    >
      {selected && (
        <span
          aria-hidden
          className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-cyan"
        />
      )}
      <FileText
        aria-hidden
        size={16}
        strokeWidth={1.5}
        className={cn("shrink-0", selected ? "text-cyan" : "text-text-3")}
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
