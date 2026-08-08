/** Frontend transport contracts. Mirrors the backend domain vocabulary in
 *  `limen/` — the API is authoritative for every state value below. */

export type RiskLevel = "GREEN" | "YELLOW" | "ORANGE" | "RED";

/** Certainty vocabulary from `limen.clinical.uncertainty.ClinicalCertainty`.
 *  Missing information stays UNKNOWN; it is never coerced to normal. */
export type ClinicalCertainty =
  | "KNOWN_NORMAL"
  | "KNOWN_ABNORMAL"
  | "UNKNOWN"
  | "CONFLICTING";

/** `UPLOADING` and `REMOVING` are client-side transitions while a request is in
 *  flight. Every other value must come from the backend. */
export type DocumentStatus =
  | "UPLOADING"
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
  | "patient_statement"
  | "clinical_extraction"
  | "retrieval"
  | "safety_evaluation"
  | "response"
  | "escalation"
  | "session_end";

export type HealthResponse = {
  status: string;
  version: string;
  app_env: string;
  llm_provider: string;
  llm_model: string;
  database: {
    database?: string;
    schema_version?: string;
    path?: string;
  };
};

export type KnowledgeDocument = {
  document_id: string;
  source_name: string;
  status: DocumentStatus;
  version: number;
  uploaded_at: string;
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
  text: string;
  source_name: string;
  page?: number | null;
  score: number;
  version: number;
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
  input_tokens?: number | null;
  output_tokens?: number | null;
  llm_calls?: number | null;
  rag_queries?: number | null;
  estimated_cost_usd?: number | null;
};

export type TraceEventRecord = {
  event_id: string;
  call_id: string;
  sequence: number;
  stage: TraceStage;
  timestamp: string;
  label: string;
  detail?: string | null;
  risk?: RiskLevel | null;
  escalate?: boolean | null;
  reasons?: string[];
  evidence?: EvidenceChunk[];
  metrics?: TurnMetrics | null;
};

export type CallTrace = {
  call_id: string;
  events: TraceEventRecord[];
  final_risk: RiskLevel | null;
  escalated: boolean;
  totals?: TurnMetrics | null;
};

/** Realtime envelope (FRONTEND.md section 29). Discriminated on `type`; the
 *  socket transport itself lands with the voice backend. */
export type RealtimeEvent =
  | { type: "call.state"; call_id: string; sequence: number; timestamp: string; payload: { state: CallPhase } }
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
      payload: TurnMetrics;
    }
  | {
      type: "call.error";
      call_id: string;
      sequence: number;
      timestamp: string;
      payload: { code: string; message: string };
    }
  | {
      type: "call.ended";
      call_id: string;
      sequence: number;
      timestamp: string;
      payload: { reason: string };
    };

export type RealtimeEventType = RealtimeEvent["type"];
