import { beforeEach, describe, expect, it } from "vitest";

import type { TranscriptTurnRecord } from "../api/types";
import { canTransition, useCallStore } from "./call-store";

const turn = (
  overrides: Partial<TranscriptTurnRecord> = {},
): TranscriptTurnRecord => ({
  turn_id: "t1",
  speaker: "agent",
  text: "Voy a hacerle unas preguntas.",
  timestamp: new Date("2026-01-01T10:00:00Z").toISOString(),
  ...overrides,
});

describe("call phase transitions", () => {
  beforeEach(() => {
    useCallStore.getState().reset();
  });

  it("requires microphone acquisition before listening", () => {
    expect(canTransition("IDLE", "LISTENING")).toBe(false);
    expect(canTransition("IDLE", "REQUESTING_MIC")).toBe(true);
    expect(canTransition("REQUESTING_MIC", "LISTENING")).toBe(true);
  });

  it("ignores illegal transitions instead of misreporting the session", () => {
    const store = useCallStore.getState();
    store.setPhase("SPEAKING");

    expect(useCallStore.getState().phase).toBe("IDLE");
  });

  it("allows barge-in from SPEAKING through INTERRUPTED back to LISTENING", () => {
    expect(canTransition("SPEAKING", "INTERRUPTED")).toBe(true);
    expect(canTransition("INTERRUPTED", "LISTENING")).toBe(true);
  });

  it("can always fail or end from any live phase", () => {
    for (const phase of ["LISTENING", "PROCESSING_STT", "THINKING", "SPEAKING"] as const) {
      expect(canTransition(phase, "ERROR")).toBe(true);
      expect(canTransition(phase, "ENDED")).toBe(true);
    }
  });

  it("records the session start when listening begins", () => {
    const store = useCallStore.getState();
    store.setPhase("REQUESTING_MIC");
    store.setPhase("LISTENING");

    expect(useCallStore.getState().startedAt).toBeTypeOf("number");
  });
});

describe("call session data", () => {
  beforeEach(() => {
    useCallStore.getState().reset();
  });

  it("preserves an interrupted agent turn for the trace", () => {
    const store = useCallStore.getState();
    store.appendTurn(turn({ turn_id: "a1", speaker: "agent" }));
    store.appendTurn(turn({ turn_id: "p1", speaker: "patient", text: "Espere" }));
    store.appendTurn(turn({ turn_id: "a2", speaker: "agent" }));

    useCallStore.getState().markLastAgentTurnInterrupted();
    const transcript = useCallStore.getState().transcript;

    expect(transcript).toHaveLength(3);
    expect(transcript[2].interrupted).toBe(true);
    expect(transcript[0].interrupted).toBeUndefined();
  });

  it("carries a microphone failure as explanatory text", () => {
    useCallStore.getState().fail({
      code: "PERMISSION_DENIED",
      message: "Microphone access is blocked.",
    });
    const state = useCallStore.getState();

    expect(state.phase).toBe("ERROR");
    expect(state.error?.message).not.toMatch(/something went wrong/i);
    expect(state.micLevel).toBe(0);
  });

  it("starts with no risk assessed and no fabricated clinical state", () => {
    const state = useCallStore.getState();

    expect(state.risk).toBeNull();
    expect(state.clinicalState).toBeNull();
    expect(state.evidence).toEqual([]);
    expect(state.metrics).toBeNull();
  });
});
