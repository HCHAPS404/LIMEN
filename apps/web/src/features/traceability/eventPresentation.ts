import type { TraceEventRecord } from "../../api/types";

/** Visual accent for a timeline category (never alone as the only cue). */
export type TraceCategoryAccent =
  | "neutral"
  | "voice"
  | "clinical"
  | "evidence"
  | "safety"
  | "response"
  | "escalation"
  | "error";

const ACCENT_TOKEN: Record<TraceCategoryAccent, string> = {
  neutral: "var(--limen-text-2)",
  voice: "var(--limen-cyan)",
  clinical: "var(--limen-violet)",
  evidence: "var(--limen-teal)",
  safety: "var(--limen-amber)",
  response: "var(--limen-violet)",
  escalation: "var(--limen-coral)",
  error: "var(--limen-coral)",
};

/** Canonical event_type (or stage fallback) → category bucket for chrome. */
const EVENT_CATEGORY: Record<string, TraceCategoryAccent> = {
  "call.started": "neutral",
  "call.completed": "neutral",
  "turn.received": "voice",
  "turn.processing.started": "clinical",
  "turn.completed": "neutral",
  "clinical.extraction.started": "clinical",
  "clinical.extraction.completed": "clinical",
  "clinical.state.updated": "clinical",
  "clinical.uncertainty.completed": "safety",
  "retrieval.started": "evidence",
  "retrieval.dense.completed": "evidence",
  "retrieval.lexical.completed": "evidence",
  "retrieval.fusion.completed": "evidence",
  "retrieval.evidence.selected": "evidence",
  "safety.evaluation.completed": "safety",
  "response.generation.started": "response",
  "response.generation.completed": "response",
  "response.fallback": "response",
  "voice.mic.requested": "voice",
  "voice.mic.granted": "voice",
  "voice.speech.started": "voice",
  "voice.speech.ended": "voice",
  "voice.audio.upload.completed": "voice",
  "voice.playback.started": "response",
  "voice.playback.completed": "response",
  "voice.interrupted": "voice",
  "voice.patient_cutoff": "voice",
  "voice.false_barge_in": "voice",
  "stt.started": "voice",
  "stt.completed": "voice",
  "tts.started": "response",
  "tts.first_audio": "response",
  "tts.completed": "response",
  "conversation.context.built": "clinical",
  "conversation.pending_question": "clinical",
  "conversation.question.answered": "clinical",
  "conversation.response.interrupted": "response",
  "conversation.intent.pending": "clinical",
  "conversation.intent.completed": "clinical",
  "escalation.artifact.persisted": "escalation",
  "provider.error": "error",
  // Legacy stage aliases
  patient_statement: "voice",
  clinical_extraction: "clinical",
  uncertainty: "safety",
  retrieval: "evidence",
  safety_evaluation: "safety",
  response: "response",
  escalation: "escalation",
  session_end: "neutral",
  conversation: "clinical",
  voice: "voice",
  stt: "voice",
  tts: "response",
};

/** Stage string → category i18n key (trace.categories.*). */
const STAGE_CATEGORY_KEY: Record<string, string> = {
  "call.started": "call",
  "call.completed": "call",
  session_end: "call",
  patient_statement: "patient",
  "turn.received": "patient",
  clinical_extraction: "clinical",
  "clinical.extraction.started": "clinical",
  "clinical.extraction.completed": "clinical",
  "clinical.state.updated": "clinical",
  uncertainty: "uncertainty",
  "clinical.uncertainty.completed": "uncertainty",
  retrieval: "retrieval",
  "retrieval.started": "retrieval",
  "retrieval.dense.completed": "retrieval",
  "retrieval.lexical.completed": "retrieval",
  "retrieval.fusion.completed": "retrieval",
  "retrieval.evidence.selected": "retrieval",
  safety_evaluation: "safety",
  "safety.evaluation.completed": "safety",
  response: "response",
  "response.generation.started": "response",
  "response.generation.completed": "response",
  "response.fallback": "response",
  escalation: "escalation",
  "escalation.artifact.persisted": "escalation",
  "provider.error": "error",
  voice: "voice",
  stt: "transcription",
  tts: "speechSynthesis",
  conversation: "conversation",
  "turn.processing.started": "reasoning",
  "turn.completed": "call",
};

export function resolveEventType(event: TraceEventRecord): string {
  return (event.event_type || event.stage || "unknown").trim();
}

/** i18next-safe key segment (dots become underscores). */
export function eventTypeKey(eventType: string): string {
  return eventType.replaceAll(".", "_");
}

export function resolveTraceCategoryKey(event: TraceEventRecord): string {
  const type = resolveEventType(event);
  if (STAGE_CATEGORY_KEY[type]) return STAGE_CATEGORY_KEY[type];
  if (STAGE_CATEGORY_KEY[event.stage]) return STAGE_CATEGORY_KEY[event.stage];
  const prefix = type.split(".")[0];
  if (prefix === "voice") return "voice";
  if (prefix === "stt") return "transcription";
  if (prefix === "tts") return "speechSynthesis";
  if (prefix === "conversation") return "conversation";
  if (prefix === "retrieval") return "retrieval";
  if (prefix === "clinical") return "clinical";
  if (prefix === "knowledge") return "knowledge";
  return "step";
}

export function resolveTraceAccent(event: TraceEventRecord): string {
  const type = resolveEventType(event);
  const bucket =
    EVENT_CATEGORY[type] ??
    EVENT_CATEGORY[event.stage] ??
    (type.startsWith("voice.") || type.startsWith("stt.")
      ? "voice"
      : type.startsWith("tts.")
        ? "response"
        : type.startsWith("retrieval.")
          ? "evidence"
          : type.startsWith("safety.") || type.startsWith("clinical.uncertainty")
            ? "safety"
            : "neutral");
  return ACCENT_TOKEN[bucket];
}

/** Pick measured numbers that actually exist on this event. */
export function collectPresentMetrics(event: TraceEventRecord): {
  key: string;
  value: number | string;
  unit?: string;
}[] {
  const m = event.metrics ?? {};
  const out: { key: string; value: number | string; unit?: string }[] = [];

  const pushNum = (key: string, raw: unknown, unit?: string) => {
    if (typeof raw === "number" && Number.isFinite(raw)) {
      out.push({ key, value: Math.round(raw * 1000) / 1000, unit });
    }
  };

  if (typeof event.duration_ms === "number" && Number.isFinite(event.duration_ms)) {
    out.push({
      key: "duration",
      value: Math.round(event.duration_ms),
      unit: "ms",
    });
  }

  pushNum(
    "latency",
    m.latency_ms ?? m.total_latency_ms,
    "ms",
  );
  pushNum("clinical", m.clinical_ms, "ms");
  pushNum("uncertainty", m.uncertainty_ms, "ms");
  pushNum("retrieval", m.retrieval_ms, "ms");
  pushNum("safety", m.safety_ms, "ms");
  pushNum("generation", m.response_generation_ms, "ms");
  pushNum("dense", m.dense_ms, "ms");
  pushNum("lexical", m.lexical_ms, "ms");
  pushNum("fusion", m.fusion_ms, "ms");
  pushNum("llmCalls", m.llm_calls);
  pushNum("inputTokens", m.input_tokens);
  pushNum("outputTokens", m.output_tokens);
  pushNum("ragQueries", m.rag_queries);
  pushNum("evidenceSelected", m.evidence_selected);

  if (
    typeof m.estimated_cost_usd === "number" &&
    Number.isFinite(m.estimated_cost_usd)
  ) {
    out.push({
      key: "estCost",
      value: `$${m.estimated_cost_usd.toFixed(4)}`,
    });
  }

  // Voice / STT timing often lands as extra keys on metrics.
  const extra = m as Record<string, unknown>;
  pushNum("voiceLatency", extra.voice_response_latency_ms, "ms");
  pushNum("stt", extra.stt_ms, "ms");
  pushNum("tts", extra.tts_ms, "ms");

  return out;
}

/** Human-facing payload facts (skip opaque blobs). */
export function collectPayloadFacts(
  payload: Record<string, unknown> | null | undefined,
): { key: string; value: string }[] {
  if (!payload || typeof payload !== "object") return [];
  const facts: { key: string; value: string }[] = [];

  const asText = (value: unknown): string | null => {
    if (value === null || value === undefined) return null;
    if (typeof value === "string") {
      const trimmed = value.trim();
      return trimmed ? trimmed : null;
    }
    if (typeof value === "number" && Number.isFinite(value)) return String(value);
    if (typeof value === "boolean") return value ? "true" : "false";
    return null;
  };

  const keys = [
    "provider",
    "model",
    "persona",
    "voice_id",
    "assistant_display_name",
    "patient_alias",
    "turn_seq",
    "turn_id",
    "bytes",
    "audio_bytes",
    "confidence",
    "stt_confidence",
    "transcript_preview",
    "fallback_reason",
    "error",
    "message",
    "finding_count",
    "chunk_count",
    "selected_chunk_ids",
    "intent",
    "question",
    "answer_preview",
  ] as const;

  for (const key of keys) {
    const raw = payload[key];
    if (Array.isArray(raw)) {
      if (raw.length === 0) continue;
      facts.push({ key, value: raw.map(String).join(", ") });
      continue;
    }
    const text = asText(raw);
    if (text !== null) facts.push({ key, value: text });
  }

  return facts;
}
