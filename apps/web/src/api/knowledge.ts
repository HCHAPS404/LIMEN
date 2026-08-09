import { apiRequest } from "./client";
import type { KnowledgeDocument, RetrievalProbe } from "./types";

export const knowledgeKeys = {
  all: ["knowledge"] as const,
  documents: () => [...knowledgeKeys.all, "documents"] as const,
  document: (id: string) => [...knowledgeKeys.all, "document", id] as const,
  probe: (id: string) => [...knowledgeKeys.all, "probe", id] as const,
};

export function listDocuments(signal?: AbortSignal): Promise<KnowledgeDocument[]> {
  return apiRequest<KnowledgeDocument[]>("/api/knowledge/documents", { signal });
}

export function uploadDocument(file: File): Promise<KnowledgeDocument> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest<KnowledgeDocument>("/api/knowledge/documents", {
    method: "POST",
    body: form,
  });
}

export function deleteDocument(documentId: string): Promise<KnowledgeDocument> {
  return apiRequest<KnowledgeDocument>(
    `/api/knowledge/documents/${encodeURIComponent(documentId)}`,
    { method: "DELETE" },
  );
}

/** Retrieval probe used to demonstrate that deleted knowledge is truly gone. */
export function verifyRetrieval(
  documentId: string,
  query: string,
): Promise<RetrievalProbe> {
  const params = new URLSearchParams({ document_id: documentId, query });
  return apiRequest<RetrievalProbe>(`/api/knowledge/retrieval-probe?${params}`);
}
