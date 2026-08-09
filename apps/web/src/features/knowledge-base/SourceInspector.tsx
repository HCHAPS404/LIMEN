import { Search, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { describeError } from "../../api/client";
import type { KnowledgeDocument } from "../../api/types";
import { EvidenceCitation } from "../../components/data/EvidenceCitation";
import { KeyValue, KeyValueList } from "../../components/data/KeyValue";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Button } from "../../components/primitives/Button";
import { Dialog } from "../../components/primitives/Dialog";
import { TextField } from "../../components/primitives/TextField";
import { formatBytes, formatTimestamp, shortHash } from "../../lib/format";
import { DocumentStatus } from "./DocumentStatus";
import { documentStatusView } from "./documentStatusView";
import { useDeleteDocument, useRetrievalProbe } from "./useKnowledge";

export function SourceInspector({
  document,
}: {
  document: KnowledgeDocument | null;
}) {
  const { t } = useTranslation("knowledge");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [query, setQuery] = useState("");
  const probe = useRetrievalProbe();
  const remove = useDeleteDocument();

  if (!document) {
    return (
      <EmptyState
        density="inline"
        eyebrow={t("inspector.emptyEyebrow")}
        title={t("inspector.emptyTitle")}
        description={t("inspector.emptyBody")}
      />
    );
  }

  const view = documentStatusView[document.status];

  return (
    <div className="flex min-h-0 flex-col gap-5">
      <div className="flex flex-col gap-2">
        <h3 className="type-h3 m-0 break-words text-white-ice">
          {document.source_name}
        </h3>
        <div className="flex items-center gap-2">
          <DocumentStatus status={document.status} />
        </div>
        <p className="type-body-s m-0 text-text-2">{view.meaning}</p>
      </div>

      <KeyValueList>
        <KeyValue label="Document ID" value={document.document_id} mono />
        <KeyValue label="Version" value={document.version} mono />
        <KeyValue
          label="SHA-256"
          value={document.sha256 ? shortHash(document.sha256) : null}
          mono
        />
        <KeyValue label="Pages" value={document.page_count} mono />
        <KeyValue label="Chunks" value={document.chunk_count} mono />
        <KeyValue
          label="Size"
          value={document.size_bytes ? formatBytes(document.size_bytes) : null}
          mono
        />
        <KeyValue label="Parser" value={document.parser} />
        <KeyValue
          label="OCR"
          value={
            document.ocr_applied === null || document.ocr_applied === undefined
              ? null
              : document.ocr_applied
                ? "Applied"
                : "Not needed"
          }
        />
        <KeyValue
          label="Uploaded"
          value={formatTimestamp(document.uploaded_at)}
        />
      </KeyValueList>

      {document.status === "FAILED" && (
        <ErrorState
          title={`Ingestion failed for ${document.source_name}`}
          stage={document.failure_stage ?? "unknown stage"}
          message={
            document.failure_message ??
            "The backend did not report a failure reason. Re-upload the document to retry ingestion."
          }
        />
      )}

      <div className="flex flex-col gap-3 pt-2">
        <TextField
          label={t("inspector.probeLabel")}
          placeholder={t("inspector.probePlaceholder")}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          hint={t("inspector.probeHint")}
        />
        <Button
          variant="secondary"
          size="sm"
          icon={<Search aria-hidden size={14} />}
          loading={probe.isPending}
          disabled={query.trim().length === 0}
          onClick={() =>
            probe.mutate({ documentId: document.document_id, query: query.trim() })
          }
        >
          {t("inspector.verify")}
        </Button>

        {probe.isError && (
          <ErrorState
            title={t("inspector.probeUnavailable")}
            message={describeError(probe.error)}
          />
        )}

        {probe.isSuccess &&
          (probe.data.chunks.length === 0 ? (
            <p className="type-body-s m-0 text-amber">
              {t("inspector.noChunks")}
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {probe.data.chunks.map((chunk) => (
                <EvidenceCitation key={chunk.chunk_id} chunk={chunk} />
              ))}
            </div>
          ))}
      </div>

      <div className="mt-auto pt-2">
        <Button
          variant="destructive"
          icon={<Trash2 aria-hidden size={16} />}
          disabled={document.status === "REMOVED" || remove.isPending}
          loading={remove.isPending}
          onClick={() => setConfirmOpen(true)}
        >
          {t("inspector.delete")}
        </Button>
        {remove.isError && (
          <ErrorState
            title={t("inspector.deleteFailed")}
            message={describeError(remove.error)}
            className="mt-3"
          />
        )}
      </div>

      <Dialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("inspector.deleteTitle")}
        description={t("inspector.deleteBody", {
          name: document.source_name,
        })}
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
              {t("inspector.keep")}
            </Button>
            <Button
              variant="destructive"
              loading={remove.isPending}
              onClick={() => {
                remove.mutate(document.document_id, {
                  onSettled: () => setConfirmOpen(false),
                });
              }}
            >
              {t("inspector.deleteNamed", { name: document.source_name })}
            </Button>
          </>
        }
      />
    </div>
  );
}
