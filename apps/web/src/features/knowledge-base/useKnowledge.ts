import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  deleteDocument,
  knowledgeKeys,
  listDocuments,
  uploadDocument,
  verifyRetrieval,
} from "../../api/knowledge";
import type { KnowledgeDocument } from "../../api/types";

/** The document list is server-owned. There is no optimistic AVAILABLE: the
 *  backend status is the only source of readiness (FRONTEND.md section 17). */
export function useDocuments() {
  return useQuery({
    queryKey: knowledgeKeys.documents(),
    queryFn: ({ signal }) => listDocuments(signal),
    // Pending ingestion states resolve on the backend, so poll while any exist.
    refetchInterval: (query) => {
      const documents = query.state.data as KnowledgeDocument[] | undefined;
      const pending = documents?.some(
        (document) =>
          document.status === "PROCESSING" ||
          document.status === "INDEXING" ||
          document.status === "UPLOADING" ||
          document.status === "REMOVING",
      );
      return pending ? 2_000 : false;
    },
  });
}

export function useUploadDocument() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: knowledgeKeys.documents() });
    },
  });
}

export function useDeleteDocument() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => deleteDocument(documentId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: knowledgeKeys.documents() });
    },
  });
}

/** Runs a retrieval query so an evaluator can confirm that a deleted document
 *  no longer contributes evidence. */
export function useRetrievalProbe() {
  return useMutation({
    mutationFn: ({ documentId, query }: { documentId: string; query: string }) =>
      verifyRetrieval(documentId, query),
  });
}
