import type { DocumentStatus } from "../../api/types";
import type { ChipTone } from "../../components/data/StatusChip";

export type DocumentStatusView = {
  label: string;
  tone: ChipTone;
  /** True while the backend is still working on the document. */
  pending: boolean;
  meaning: string;
};

/** AVAILABLE uses evidence teal, not clinical green: knowledge readiness must
 *  never be mistaken for a patient risk signal (FRONTEND.md section 8). */
export const documentStatusView: Record<DocumentStatus, DocumentStatusView> = {
  UPLOADING: {
    label: "Uploading",
    tone: "intelligence",
    pending: true,
    meaning: "Transferring the file to the backend.",
  },
  PROCESSING: {
    label: "Processing",
    tone: "review",
    pending: true,
    meaning: "Parsing and OCR in progress. Not retrievable yet.",
  },
  INDEXING: {
    label: "Indexing",
    tone: "review",
    pending: true,
    meaning: "Chunking and embedding in progress. Not retrievable yet.",
  },
  AVAILABLE: {
    label: "Available",
    tone: "evidence",
    pending: false,
    meaning: "Indexed and retrievable by the clinical agent.",
  },
  FAILED: {
    label: "Failed",
    tone: "escalation",
    pending: false,
    meaning: "Ingestion failed. Nothing from this document is retrievable.",
  },
  REMOVING: {
    label: "Removing",
    tone: "review",
    pending: true,
    meaning: "Deleting chunks and embeddings.",
  },
  REMOVED: {
    label: "Removed",
    tone: "neutral",
    pending: false,
    meaning: "Deleted. All retrieval material for this document is gone.",
  },
};
