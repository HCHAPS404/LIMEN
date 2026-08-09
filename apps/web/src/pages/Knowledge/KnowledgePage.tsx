import { Database, PanelRight, RefreshCw } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, describeError } from "../../api/client";
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
  const { t } = useTranslation("knowledge");
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
          <InspectorPanel title={t("selectedSource")} scroll className="h-full">
            <SourceInspector document={selected} />
          </InspectorPanel>
        ) : undefined
      }
    >
      <GlassPanel
        title={t("title")}
        actions={
          <div className="flex items-center gap-3">
            <span className="type-metric-sm tabular text-text-2">
              {t("availableCount", { count: availableCount })}
            </span>
            <IconButton
              label={t("refresh")}
              icon={<RefreshCw aria-hidden size={16} />}
              onClick={() => void documents.refetch()}
            />
            {!isDesktop && (
              <IconButton
                label={t("openSelected")}
                icon={<PanelRight aria-hidden size={16} />}
                onClick={() => setInspectorOpen(true)}
              />
            )}
          </div>
        }
        scroll
        className="min-h-0 flex-1"
      >
        <div className="flex flex-col gap-6">
          <UploadDropzone
            busy={upload.isPending}
            disabled={endpointMissing}
            disabledReason={
              endpointMissing ? t("upload.disabled501") : undefined
            }
            onFiles={(files) => {
              for (const file of files) upload.mutate(file);
            }}
          />

          {upload.isError && (
            <ErrorState
              title={t("uploadFailed")}
              stage="upload"
              message={describeError(upload.error)}
              onRetry={() => upload.reset()}
              retryLabel={t("dismiss")}
            />
          )}

          {documents.isPending && (
            <LoadingState label={t("loading")} rows={4} />
          )}

          {documents.isError &&
            (endpointMissing ? (
              <EmptyState
                density="inline"
                eyebrow={t("title")}
                title={t("emptyApiTitle")}
                description={describeError(documents.error)}
              />
            ) : (
              <ErrorState
                title={t("loadError")}
                message={describeError(documents.error)}
                onRetry={() => void documents.refetch()}
              />
            ))}

          {documents.isSuccess &&
            (list.length === 0 ? (
              <EmptyState
                density="inline"
                eyebrow={t("emptyEyebrow")}
                title={t("emptyTitle")}
                description={t("emptyBody")}
                icon={<Database aria-hidden size={22} />}
              />
            ) : (
              <ul className="m-0 flex list-none flex-col p-0">
                {list.map((item) => (
                  <li
                    key={item.document_id}
                    className="border-b border-[color-mix(in_oklab,var(--glass-border)_50%,transparent)] last:border-b-0"
                  >
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
          title={t("selectedSource")}
        >
          <SourceInspector document={selected} />
        </Drawer>
      )}
    </WorkspaceSplit>
  );
}
