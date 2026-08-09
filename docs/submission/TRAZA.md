# TRAZA — turn reconstruction (submission)

TRAZA is LIMEN's inspectable decision trace. It reconstructs **what happened**,
not hidden model reasoning.

## One voice turn (conceptual)

```mermaid
sequenceDiagram
  participant B as Browser
  participant API as LIMEN API
  participant STT as Faster-Whisper
  participant ORCH as Orchestrator
  participant RAG as Hybrid RAG
  participant SG as SafetyGovernor
  participant LLM as Phi-3.5 / template
  participant TTS as Piper
  participant DB as SQLite TRAZA

  B->>API: voice.speech.ended
  API->>STT: audio
  STT-->>API: transcript
  API->>ORCH: text turn
  ORCH->>ORCH: clinical_extraction
  ORCH->>ORCH: uncertainty
  ORCH->>RAG: retrieve (if needed)
  RAG-->>ORCH: EvidenceChunk + provenance
  ORCH->>SG: floor + enforce_floor
  SG-->>ORCH: SafetyDecision
  ORCH->>LLM: constrained generation
  LLM-->>ORCH: candidate text
  ORCH->>ORCH: response validator
  ORCH->>TTS: synthesize
  TTS-->>API: audio
  API->>B: playback + voice.playback.started
  ORCH->>DB: staged TraceEvents
```

## Typical TRAZA stages

`call.started` → `patient_statement` → `clinical_extraction` → `uncertainty` →
`retrieval` → `safety_evaluation` → `conversation` → `response` →
voice provider events (when applicable) → `session_end`

## Provenance

Retrieved evidence references include document id, chunk id, source name, and
page when available. Inspectors must verify content support — IDs alone are not
proof.

## UI / API

- UI: `/trace/:callId`
- API: `GET /api/traces/{call_id}`

No chain-of-thought is stored.
