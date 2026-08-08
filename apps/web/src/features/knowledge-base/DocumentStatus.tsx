import { LoaderCircle } from "lucide-react";

import type { DocumentStatus as DocumentStatusValue } from "../../api/types";
import { StatusChip } from "../../components/data/StatusChip";
import { documentStatusView } from "./documentStatusView";

export function DocumentStatus({ status }: { status: DocumentStatusValue }) {
  const view = documentStatusView[status];

  return (
    <StatusChip
      tone={view.tone}
      title={view.meaning}
      icon={
        view.pending ? (
          <LoaderCircle aria-hidden size={11} className="animate-spin" />
        ) : undefined
      }
    >
      {view.label}
    </StatusChip>
  );
}
