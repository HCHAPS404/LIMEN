import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { KnowledgeDocument } from "../../api/types";
import { renderRoute } from "../../test/renderRoute";

const documents: KnowledgeDocument[] = [
  {
    document_id: "doc-1",
    source_name: "protocolo-alta.pdf",
    status: "AVAILABLE",
    version: 2,
    uploaded_at: "2026-01-04T09:30:00Z",
    size_bytes: 240_512,
    page_count: 18,
    chunk_count: 64,
    sha256: "9f2c4d1a77bb0e5531aa77c0d9e4f1b2c3d4e5f60718293a4b5c6d7e8f901234",
    parser: "pdfplumber",
    ocr_applied: false,
  },
  {
    document_id: "doc-2",
    source_name: "escaneo-consulta.pdf",
    status: "INDEXING",
    version: 1,
    uploaded_at: "2026-01-04T10:05:00Z",
  },
  {
    document_id: "doc-3",
    source_name: "roto.pdf",
    status: "FAILED",
    version: 1,
    uploaded_at: "2026-01-04T10:10:00Z",
    failure_stage: "ocr",
    failure_message: "Tesseract could not read pages 4-7.",
  },
];

function mockKnowledge(response: {
  status: number;
  body?: unknown;
}) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/health")) {
        return Promise.resolve(
          new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
        );
      }
      return Promise.resolve(
        new Response(
          response.body === undefined ? null : JSON.stringify(response.body),
          { status: response.status },
        ),
      );
    }),
  );
}

describe("Knowledge console", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists sources with the status reported by the backend", async () => {
    mockKnowledge({ status: 200, body: documents });

    renderRoute("/knowledge");

    expect(await screen.findByText("protocolo-alta.pdf")).toBeInTheDocument();
    expect(screen.getByText("Available")).toBeInTheDocument();
    expect(screen.getByText("Indexing")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("1 disponible")).toBeInTheDocument();
  });

  it("exposes provenance and the failure reason for a selected source", async () => {
    mockKnowledge({ status: 200, body: documents });

    renderRoute("/knowledge");

    fireEvent.click(await screen.findByText("roto.pdf"));

    expect(
      await screen.findByText(/Tesseract could not read pages 4-7/),
    ).toBeInTheDocument();
    expect(screen.getByText("ocr")).toBeInTheDocument();
  });

  it("says the knowledge API is unavailable instead of showing sources", async () => {
    mockKnowledge({ status: 501, body: { detail: "Not Implemented" } });

    renderRoute("/knowledge");

    expect(
      await screen.findByText(/API de conocimiento no implementada/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("Available")).not.toBeInTheDocument();
    expect(screen.getByText("0 disponibles")).toBeInTheDocument();
  });

  it("disables ingestion when the upload endpoint does not exist", async () => {
    mockKnowledge({ status: 501, body: { detail: "Not Implemented" } });

    renderRoute("/knowledge");

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /elegir archivo/i }),
      ).toBeDisabled(),
    );
    expect(
      screen.getByText(/no implementada \(HTTP 501\)/i),
    ).toBeInTheDocument();
  });

  it("names the document in the delete confirmation", async () => {
    mockKnowledge({ status: 200, body: documents });

    renderRoute("/knowledge");

    fireEvent.click(await screen.findByText("protocolo-alta.pdf"));
    fireEvent.click(
      await screen.findByRole("button", { name: /eliminar fuente/i }),
    );

    const dialog = await screen.findByRole("dialog", {
      name: /eliminar esta fuente/i,
    });
    expect(dialog).toHaveTextContent("protocolo-alta.pdf");
    expect(dialog).toHaveTextContent(/ya no recuperará nada de ella/i);
  });
});
