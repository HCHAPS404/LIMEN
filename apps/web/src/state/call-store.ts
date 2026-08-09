import { create } from "zustand";

import type {
  CallPhase,
  ClinicalStateSnapshot,
  EvidenceChunk,
  RiskLevel,
  TranscriptTurnRecord,
  TurnMetrics,
} from "../api/types";

/** Legal phase transitions for the voice session (FRONTEND.md section 16).
 *  Keeping them explicit means an out-of-order backend event cannot put the UI
 *  into a state that misrepresents what the system is doing. */
export const CALL_TRANSITIONS: Record<CallPhase, readonly CallPhase[]> = {
  IDLE: ["REQUESTING_MIC", "ERROR", "ENDED"],
  REQUESTING_MIC: ["LISTENING", "ERROR", "IDLE"],
  LISTENING: ["PROCESSING_STT", "SPEAKING", "ERROR", "ENDED"],
  PROCESSING_STT: ["THINKING", "LISTENING", "ERROR", "ENDED"],
  THINKING: ["SPEAKING", "LISTENING", "ERROR", "ENDED"],
  SPEAKING: ["INTERRUPTED", "LISTENING", "ERROR", "ENDED"],
  INTERRUPTED: ["LISTENING", "ERROR", "ENDED"],
  ERROR: ["IDLE", "REQUESTING_MIC", "ENDED"],
  ENDED: ["IDLE"],
};

export function canTransition(from: CallPhase, to: CallPhase): boolean {
  return from === to || CALL_TRANSITIONS[from].includes(to);
}

export type CallError = {
  code: string;
  /** Explains what failed in words, never "Something went wrong." */
  message: string;
};

type CallState = {
  phase: CallPhase;
  callId: string | null;
  startedAt: number | null;
  micLevel: number;
  patientSpeaking: boolean;
  error: CallError | null;
  transcript: TranscriptTurnRecord[];
  clinicalState: ClinicalStateSnapshot | null;
  risk: RiskLevel | null;
  safetyReasons: string[];
  escalated: boolean;
  evidence: EvidenceChunk[];
  metrics: TurnMetrics | null;
  /** Call-scoped assistant name (frozen for the live session). */
  assistantDisplayName: string | null;
  /** Voice WebSocket — distinct from HTTP /health "Connected". */
  transportStatus: "idle" | "connecting" | "open" | "closed" | "error";

  setPhase: (phase: CallPhase) => void;
  /** Backend realtime may jump phases; do not drop the authoritative state. */
  applyServerPhase: (phase: CallPhase) => void;
  setCallId: (callId: string | null) => void;
  setAssistantDisplayName: (name: string | null) => void;
  setMicLevel: (level: number) => void;
  setPatientSpeaking: (speaking: boolean) => void;
  setTransportStatus: (
    status: "idle" | "connecting" | "open" | "closed" | "error",
  ) => void;
  fail: (error: CallError) => void;
  appendTurn: (turn: TranscriptTurnRecord) => void;
  markLastAgentTurnInterrupted: () => void;
  setClinicalState: (state: ClinicalStateSnapshot) => void;
  setSafety: (risk: RiskLevel, escalate: boolean, reasons: string[]) => void;
  setEvidence: (chunks: EvidenceChunk[]) => void;
  setMetrics: (metrics: TurnMetrics) => void;
  reset: () => void;
};

const initial = {
  phase: "IDLE" as CallPhase,
  callId: null,
  startedAt: null,
  micLevel: 0,
  patientSpeaking: false,
  error: null,
  transcript: [] as TranscriptTurnRecord[],
  clinicalState: null,
  risk: null,
  safetyReasons: [] as string[],
  escalated: false,
  evidence: [] as EvidenceChunk[],
  metrics: null,
  assistantDisplayName: null as string | null,
  transportStatus: "idle" as const,
};

export const useCallStore = create<CallState>((set, get) => ({
  ...initial,

  setPhase: (phase) => {
    const current = get().phase;
    if (!canTransition(current, phase)) return;
    set({
      phase,
      startedAt:
        phase === "LISTENING" && get().startedAt === null
          ? Date.now()
          : get().startedAt,
      error: phase === "ERROR" ? get().error : null,
    });
  },

  applyServerPhase: (phase) => {
    set({
      phase,
      startedAt:
        (phase === "LISTENING" || phase === "THINKING" || phase === "SPEAKING") &&
        get().startedAt === null
          ? Date.now()
          : get().startedAt,
      error: phase === "ERROR" ? get().error : null,
    });
  },

  setCallId: (callId) => set({ callId }),
  setAssistantDisplayName: (assistantDisplayName) => set({ assistantDisplayName }),
  setMicLevel: (micLevel) => set({ micLevel }),
  setPatientSpeaking: (patientSpeaking) => set({ patientSpeaking }),
  setTransportStatus: (transportStatus) => set({ transportStatus }),

  fail: (error) => set({ phase: "ERROR", error, micLevel: 0 }),

  appendTurn: (turn) =>
    set((state) => ({ transcript: [...state.transcript, turn] })),

  /** Barge-in must preserve the interrupted agent turn for the trace. */
  markLastAgentTurnInterrupted: () =>
    set((state) => {
      const index = [...state.transcript]
        .reverse()
        .findIndex((turn) => turn.speaker === "agent");
      if (index === -1) return state;
      const target = state.transcript.length - 1 - index;
      const transcript = [...state.transcript];
      transcript[target] = { ...transcript[target], interrupted: true };
      return { transcript };
    }),

  setClinicalState: (clinicalState) => set({ clinicalState }),
  setSafety: (risk, escalate, reasons) =>
    set({ risk, escalated: escalate, safetyReasons: reasons }),
  setEvidence: (evidence) => set({ evidence }),
  setMetrics: (metrics) => set({ metrics }),

  reset: () => set({ ...initial }),
}));
