import { Database, PanelRight, RefreshCw } from "lucide-react";
import { useState } from "react";

import { ApiError, describeError } from "../../api/client";
import { StatusChip } from "../../components/data/StatusChip";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { GlassPanel, InspectorPanel } from "../../components/glass/Panel";
import { Drawer } from "../../components/primitives/Drawer";
import { IconButton } from "../../components/primitives/IconButton";
import { WorkspaceSplit } from "../../components/shell/AppShell";
import { DocumentRow } from "../../features/knowledge-base/DocumentRow";
import { SourceInspector } from "../../features/knowledge-base/SourceInspector";
import { UploadDropzone } from "../../features/knowledge-base/UploadDropzone";
import {
  useDocuments,
  useUploadDocument,
} from "../../features/knowledge-base/useKnowledge";
import { useIsDesktop } from "../../hooks/useMediaQuery";

export function KnowledgePage() {
  const documents = useDocuments();
  const upload = useUploadDocument();
  const isDesktop = useIsDesktop();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);

  const list = documents.data ?? [];
  const selected = list.find((item) => item.document_id === selectedId) ?? null;

  const endpointMissing =
    documents.error instanceof ApiError && documents.error.isNotImplemented;
  const availableCount = list.filter((item) => item.status === "AVAILABLE").length;

  return (
    <WorkspaceSplit
      inspector={
        isDesktop ? (
          <InspectorPanel title="Selected source" scroll className="h-full">
            <SourceInspector document={selected} />
          </InspectorPanel>
        ) : undefined
      }
    >
      <GlassPanel
        title="Knowledge base"
        actions={
          <div className="flex items-center gap-2">
            <StatusChip tone={availableCount > 0 ? "evidence" : "neutral"}>
              {availableCount} available
            </StatusChip>
            <IconButton
              label="Refresh document list"
              icon={<RefreshCw aria-hidden size={16} />}
              onClick={() => void documents.refetch()}
            />
            {!isDesktop && (
              <IconButton
                label="Open selected source"
                icon={<PanelRight aria-hidden size={16} />}
                onClick={() => setInspectorOpen(true)}
              />
            )}
          </div>
        }
        scroll
        className="min-h-0 flex-1"
      >
        <div className="flex flex-col gap-5">
          <UploadDropzone
            busy={upload.isPending}
            disabled={endpointMissing}
            disabledReason={
              endpointMissing
                ? "Knowledge ingestion is marked not implemented (HTTP 501)."
                : undefined
            }
            onFiles={(files) => {
              for (const file of files) upload.mutate(file);
            }}
          />

          {upload.isError && (
            <ErrorState
              title="Upload failed"
              stage="upload"
              message={describeError(upload.error)}
              onRetry={() => upload.reset()}
              retryLabel="Dismiss"
            />
          )}

          {documents.isPending && (
            <LoadingState label="Loading sources" rows={4} />
          )}

          {documents.isError &&
            (endpointMissing ? (
              <EmptyState
                eyebrow="Knowledge"
                title="Knowledge API not implemented"
                description={describeError(documents.error)}
              />
            ) : (
              <ErrorState
                title="Could not load sources"
                message={describeError(documents.error)}
                onRetry={() => void documents.refetch()}
              />
            ))}

          {documents.isSuccess &&
            (list.length === 0 ? (
              <EmptyState
                eyebrow="Empty"
                title="No clinical sources yet"
                description="Add a protocol or discharge instruction PDF. The agent can only cite documents that reach AVAILABLE."
                icon={<Database aria-hidden size={22} />}
              />
            ) : (
              <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
                {list.map((item) => (
                  <li key={item.document_id}>
                    <DocumentRow
                      document={item}
                      selected={item.document_id === selectedId}
                      onSelect={() => {
                        setSelectedId(item.document_id);
                        if (!isDesktop) setInspectorOpen(true);
                      }}
                    />
                  </li>
                ))}
              </ul>
            ))}
        </div>
      </GlassPanel>

      {!isDesktop && (
        <Drawer
          open={inspectorOpen}
          onOpenChange={setInspectorOpen}
          title="Selected source"
        >
          <SourceInspector document={selected} />
        </Drawer>
      )}
    </WorkspaceSplit>
  );
}
