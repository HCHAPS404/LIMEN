/** Frontend transport contracts. Mirrors the backend domain vocabulary in
 *  `limen/` — the API is authoritative for every state value below. */

export type RiskLevel = "GREEN" | "YELLOW" | "ORANGE" | "RED";

/** Certainty vocabulary from `limen.clinical.uncertainty.ClinicalCertainty`.
 *  Missing information stays UNKNOWN; it is never coerced to normal. */
export type ClinicalCertainty =
  | "KNOWN_NORMAL"
  | "KNOWN_ABNORMAL"
  | "IMPROVING"
  | "UNKNOWN"
  | "CONFLICTING";

/** Backend lifecycle statuses plus client-only optimistic `UPLOADING` / `INDEXING`. */
export type DocumentStatus =
  | "UPLOADING"
  | "UPLOADED"
  | "PROCESSING"
  | "INDEXING"
  | "AVAILABLE"
  | "FAILED"
  | "REMOVING"
  | "REMOVED";

export type CallPhase =
  | "IDLE"
  | "REQUESTING_MIC"
  | "LISTENING"
  | "PROCESSING_STT"
  | "THINKING"
  | "SPEAKING"
  | "INTERRUPTED"
  | "ERROR"
  | "ENDED";

export type TraceStage =
  | "call.started"
  | "patient_statement"
  | "clinical_extraction"
  | "uncertainty"
  | "retrieval"
  | "safety_evaluation"
  | "response"
  | "conversation"
  | "voice"
  | "stt"
  | "tts"
  | "escalation"
  | "session_end"
  | "provider.error";

export type HealthResponse = {
  status: string;
  version: string;
  app_env: string;
  llm_provider: string;
  llm_model: string;
  degraded_llm_mode?: boolean;
  database: {
    database?: string;
    schema_version?: string;
    path?: string;
  };
};

export type KnowledgeDocument = {
  document_id: string;
  source_name: string;
  filename?: string | null;
  status: DocumentStatus;
  version: number;
  active_version_id?: string | null;
  uploaded_at: string;
  updated_at?: string | null;
  indexed_at?: string | null;
  removed_at?: string | null;
  size_bytes?: number | null;
  page_count?: number | null;
  chunk_count?: number | null;
  sha256?: string | null;
  parser?: string | null;
  ocr_applied?: boolean | null;
  failure_stage?: string | null;
  failure_message?: string | null;
};

export type EvidenceChunk = {
  document_id: string;
  chunk_id: string;
  /** Full or preview text; traces may send `text_preview` instead. */
  text?: string;
  text_preview?: string;
  source_name: string;
  filename?: string | null;
  page?: number | null;
  section?: string | null;
  score: number;
  version?: number;
  version_id?: string | null;
  content_hash?: string | null;
  active?: boolean;
};

export type RetrievalProbe = {
  query: string;
  executed_at: string;
  chunks: EvidenceChunk[];
};

export type Finding = {
  name: string;
  certainty: ClinicalCertainty;
  notes?: string | null;
};

export type ClinicalStateSnapshot = {
  findings: Finding[];
  open_questions: string[];
  summary_notes?: string | null;
};

export type TranscriptTurnRecord = {
  turn_id: string;
  speaker: "patient" | "agent";
  text: string;
  timestamp: string;
  interrupted?: boolean;
};

export type CallSummary = {
  call_id: string;
  patient_alias: string;
  procedure?: string | null;
  postoperative_day?: number | null;
  started_at: string;
  duration_seconds?: number | null;
  final_risk: RiskLevel | null;
  escalated: boolean;
};

export type TurnMetrics = {
  latency_ms?: number | null;
  total_latency_ms?: number | null;
  clinical_ms?: number | null;
  uncertainty_ms?: number | null;
  retrieval_ms?: number | null;
  safety_ms?: number | null;
  response_generation_ms?: number | null;
  persistence_ms?: number | null;
  dense_ms?: number | null;
  lexical_ms?: number | null;
  fusion_ms?: number | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  llm_calls?: number | null;
  rag_queries?: number | null;
  evidence_selected?: number | null;
  estimated_cost_usd?: number | null;
  cost_basis?: "measured" | "estimated" | "not_available" | "synthetic" | null;
};

export type TraceEventRecord = {
  event_id: string;
  call_id: string;
  sequence: number;
  stage: TraceStage | string;
  event_type?: string | null;
  schema_version?: number;
  timestamp: string;
  label: string;
  detail?: string | null;
  risk?: RiskLevel | null;
  escalate?: boolean | null;
  reasons?: string[];
  evidence?: EvidenceChunk[];
  metrics?: TurnMetrics | null;
  turn_id?: string | null;
  document_id?: string | null;
  duration_ms?: number | null;
  status?: string | null;
  payload?: Record<string, unknown>;
};

export type CallTrace = {
  call_id: string;
  events: TraceEventRecord[];
  final_risk: RiskLevel | null;
  escalated: boolean;
  totals?: Record<string, unknown> | null;
  schema_version?: number;
};

/** Realtime envelope (FRONTEND.md section 29). Discriminated on `type`; the
 *  socket transport itself lands with the voice backend. */
export type RealtimeEvent =
  | {
      type: "call.state";
      call_id: string;
      sequence: number;
      timestamp: string;
      payload: {
        state: CallPhase;
        turn_seq?: number;
        voice_persona?: string;
        voice_display_name?: string;
      };
    }
  | {
      type: "call.transcript";
      call_id: string;
      sequence: number;
      timestamp: string;
      payload: TranscriptTurnRecord;
    }
  | {
      type: "call.clinical_state";
      call_id: string;
      sequence: number;
      timestamp: string;
      payload: ClinicalStateSnapshot;
    }
  | {
      type: "call.safety";
      call_id: string;
      sequence: number;
      timestamp: string;
      payload: { risk: RiskLevel; escalate: boolean; reasons: string[] };
    }
  | {
      type: "call.evidence";
      call_id: string;
      sequence: number;
      timestamp: string;
      payload: { chunks: EvidenceChunk[] };
    }
  | {
      type: "call.metrics";
      call_id: string;
      sequence: number;
      timestamp: string;
      payload: TurnMetrics & Record<string, unknown>;
    }
  | {
      type: "call.audio";
      call_id: string;
      sequence: number;
      timestamp: string;
      payload: {
        turn_seq: number;
        mime_type?: string;
        sample_rate_hz?: number;
      };
    }
  | {
      type: "call.error";
      call_id: string;
      sequence: number;
      timestamp: string;
      payload: {
        code: string;
        message: string;
        retryable?: boolean;
        assistant_text?: string;
      };
    }
  | {
      type: "call.ended";
      call_id: string;
      sequence: number;
      timestamp: string;
      payload: { reason: string; call_end_reason?: string };
    };

export type RealtimeEventType = RealtimeEvent["type"];
