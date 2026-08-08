import { Search, Trash2 } from "lucide-react";
import { useState } from "react";

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
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [query, setQuery] = useState("");
  const probe = useRetrievalProbe();
  const remove = useDeleteDocument();

  if (!document) {
    return (
      <EmptyState
        eyebrow="Threshold"
        title="No source selected"
        description="Choose a document to inspect its provenance, ingestion state, and retrieval behavior."
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

      <div className="flex flex-col gap-3 border-t border-glass-border pt-4">
        <TextField
          label="Retrieval probe"
          placeholder="Ask what this source should answer"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          hint="Runs a real retrieval query. After deletion it should return no chunks from this source."
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
          Verify retrieval
        </Button>

        {probe.isError && (
          <ErrorState
            title="Retrieval probe unavailable"
            message={describeError(probe.error)}
          />
        )}

        {probe.isSuccess &&
          (probe.data.chunks.length === 0 ? (
            <p className="type-body-s m-0 text-amber">
              No chunks returned for this query. This source contributes no
              evidence right now.
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {probe.data.chunks.map((chunk) => (
                <EvidenceCitation key={chunk.chunk_id} chunk={chunk} />
              ))}
            </div>
          ))}
      </div>

      <div className="mt-auto border-t border-glass-border pt-4">
        <Button
          variant="destructive"
          icon={<Trash2 aria-hidden size={16} />}
          disabled={document.status === "REMOVED" || remove.isPending}
          loading={remove.isPending}
          onClick={() => setConfirmOpen(true)}
        >
          Delete source
        </Button>
        {remove.isError && (
          <ErrorState
            title="Deletion failed"
            message={describeError(remove.error)}
            className="mt-3"
          />
        )}
      </div>

      <Dialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Delete this source?"
        description={
          <>
            <strong className="text-ice">{document.source_name}</strong> and all of
            its chunks and embeddings will be removed. The clinical agent will no
            longer retrieve anything from it.
          </>
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
              Keep source
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
              Delete {document.source_name}
            </Button>
          </>
        }
      />
    </div>
  );
}
