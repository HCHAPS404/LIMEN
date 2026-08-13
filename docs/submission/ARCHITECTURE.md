# LIMEN architecture diagram (submission)

Canonical modular-monolith architecture for Tech Sphere Challenge 2026.
Components named below exist in code (see consistency checklist at bottom).

## Export

1. Open this Mermaid in any Mermaid renderer (GitHub, mermaid.live, VS Code).
2. Export PNG/SVG for the jury package.
3. Keep this Markdown as the source of truth.

Exported PNG: [`assets/architecture.png`](assets/architecture.png).

## System architecture

```mermaid
flowchart TB
  subgraph VoiceFlow["Voice flow"]
    MIC[Browser microphone]
    VAD[Client VAD / endpointing]
    WS[WebSocket /api/calls/id/stream]
    STT[FasterWhisperSTTProvider<br/>CUDA float16]
    TTS[PiperTTSProvider<br/>es_MX-claude-high]
    PLAY[Browser playback]
    MIC --> VAD --> WS --> STT
    TTS --> WS --> PLAY
  end

  subgraph AuthorityFlow["Authority flow — Safety is final"]
    EXT[Clinical extraction]
    CS[ClinicalState]
    UNC[Uncertainty analysis]
    SG[SafetyGovernor<br/>evaluate + enforce_floor]
    SD[SafetyDecision<br/>GREEN/YELLOW/RED]
    VAL[Response validator]
    EXT --> CS --> UNC --> SG --> SD --> VAL
  end

  subgraph EvidenceFlow["Evidence flow"]
    ADMIN[Knowledge admin console]
    LIFE[Knowledge lifecycle]
    E5[multilingual-e5-small]
    QD[(Qdrant vectors)]
    FTS[(SQLite FTS5)]
    HYB[HybridEvidenceRetriever<br/>RRF]
    ADMIN --> LIFE --> E5 --> QD
    LIFE --> FTS
    QD --> HYB
    FTS --> HYB
  end

  subgraph Language["Language generation — subordinate"]
    CTX[ConversationContext]
    PHI[OllamaLLMProvider<br/>phi3.5]
    TPL[Deterministic templates]
    CTX --> PHI
    SD --> PHI
    HYB --> PHI
    SD --> TPL
    PHI --> VAL
    TPL --> VAL
  end

  subgraph Telemetry["Telemetry / TRAZA"]
    TR[Trace events]
    SQL[(SQLite calls/traces)]
    MET[Turn / call metrics]
    TR --> SQL
    MET --> SQL
  end

  STT --> EXT
  STT --> CTX
  HYB --> SG
  VAL --> TTS
  EXT --> TR
  UNC --> TR
  HYB --> TR
  SG --> TR
  PHI --> TR
  TTS --> TR
```

## Flow roles

| Flow | Meaning |
| --- | --- |
| Voice | Mic → VAD → STT → … → TTS → playback |
| Authority | ClinicalState + rules → SafetyDecision; LLM cannot downgrade |
| Evidence | Upload/index → Hybrid RAG → typed EvidenceChunk + provenance |
| Telemetry | TRAZA stages + usage/timing without chain-of-thought |

## Code consistency checklist

| Diagram node | Code |
| --- | --- |
| SafetyGovernor | `limen/safety/governor.py` |
| HybridEvidenceRetriever | `limen/knowledge/hybrid.py` |
| OllamaLLMProvider | `limen/intelligence/providers/ollama.py` |
| FasterWhisperSTTProvider | `limen/voice/providers/faster_whisper_stt.py` |
| PiperTTSProvider | `limen/voice/providers/piper_tts.py` |
| ConversationContext | `limen/conversation/context.py` |
| TRAZA | `limen/tracing/`, `apps/api/routers/traces.py` |
| Knowledge lifecycle | `limen/knowledge/ingestion.py`, `deletion.py` |
| Admin console | `apps/web` `/knowledge` |

Detailed domain boundaries: [`ARCHITECTURE.md`](../../ARCHITECTURE.md), [`BACKEND.md`](../../BACKEND.md), [`FRONTEND.md`](../../FRONTEND.md).
