import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { TraceEventRecord } from "../../api/types";
import { renderWithProviders } from "../../test/renderRoute";
import { DecisionCard } from "./DecisionCard";

function event(
  partial: Partial<TraceEventRecord> &
    Pick<TraceEventRecord, "event_id" | "stage" | "label">,
): TraceEventRecord {
  return {
    call_id: "call-1",
    sequence: 3,
    timestamp: "2026-08-09T17:37:00.000Z",
    ...partial,
  };
}

describe("DecisionCard", () => {
  it("shows a human Spanish title for voice events instead of raw keys", () => {
    renderWithProviders(
      <DecisionCard
        event={event({
          event_id: "e1",
          stage: "voice",
          event_type: "voice.speech.ended",
          label: "voice.speech.ended",
          duration_ms: 420,
        })}
      />,
    );

    expect(screen.getByText("El paciente dejó de hablar")).toBeInTheDocument();
    expect(screen.queryByText("voice.speech.ended")).not.toBeInTheDocument();
    expect(screen.getByText("Duración")).toBeInTheDocument();
    expect(screen.getByText("420")).toBeInTheDocument();
  });

  it("does not dump empty cost metrics when none were measured", () => {
    renderWithProviders(
      <DecisionCard
        event={event({
          event_id: "e2",
          stage: "voice",
          event_type: "voice.mic.granted",
          label: "voice.mic.granted",
        })}
      />,
    );

    expect(screen.getByText("Micrófono concedido")).toBeInTheDocument();
    expect(screen.queryByText("Not measured")).not.toBeInTheDocument();
    expect(
      screen.getByText(/Este paso no aporta métricas de coste/),
    ).toBeInTheDocument();
  });

  it("renders evidence text from text_preview when text is absent", () => {
    renderWithProviders(
      <DecisionCard
        event={event({
          event_id: "e3",
          stage: "retrieval",
          event_type: "retrieval.evidence.selected",
          label: "Evidence retrieval",
          evidence: [
            {
              document_id: "d1",
              chunk_id: "c1",
              source_name: "Protocolo.pdf",
              text_preview: "Controlar fiebre mayor de 38.5",
              score: 0.81,
              version: 2,
              page: 4,
            },
          ],
        })}
      />,
    );

    expect(screen.getByText("Controlar fiebre mayor de 38.5")).toBeInTheDocument();
    expect(screen.getByText(/Protocolo\.pdf/)).toBeInTheDocument();
  });
});
