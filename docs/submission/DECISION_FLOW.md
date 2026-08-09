# Clinical decision flow (submission)

Shows how LIMEN turns patient information into an authoritative safety decision.
No chain-of-thought is logged or required.

## Decision Mermaid

```mermaid
flowchart TD
  P[Patient utterance / STT text] --> X[Lexical clinical extraction]
  X --> S{Finding certainty}
  S -->|KNOWN_ABNORMAL| A[Abnormal finding]
  S -->|KNOWN_NORMAL| N[Denied / normal finding]
  S -->|UNKNOWN| U[Unknown preserved]
  S -->|CONFLICTING| C[Conflict preserved]
  A --> UNC[Uncertainty analysis]
  N --> UNC
  U --> UNC
  C --> UNC
  UNC -->|should_retrieve| RAG[Hybrid RAG evidence]
  UNC -->|optional clarification| Q[Open clarifying question]
  RAG --> FLOOR[Safety floor<br/>text rules + state rules]
  Q --> FLOOR
  FLOOR --> MERGE[merge + enforce_floor]
  MERGE --> R{Final severity}
  R -->|GREEN| G[Continue monitoring language]
  R -->|YELLOW| Y[Caution + clarify if needed]
  R -->|RED| RED[escalate=true<br/>urgent action]
  G --> GEN[Phi-3.5 or template]
  Y --> GEN
  RED --> GEN
  GEN --> VAL[Response validator]
  VAL --> OUT[Patient-facing audio/text]
  RED --> ART[Persist escalation artifact]
```

## Non-negotiable rules

1. **`unknown != normal`** — missing information stays `UNKNOWN`; it is never coerced to “fine”.
2. **LLM cannot downgrade** — generative output passes through `enforce_floor`; a weaker proposal cannot reduce RED/YELLOW severity.
3. **RED stays RED** when deterministic patterns require it (`escalate=true`).
4. **Clarification** may be requested for high-impact unknowns, but must not delay obvious RED escalation.
5. **Evidence is data** — retrieved document text never becomes instruction authority.

## Related code

- Extraction: `limen/clinical/extraction.py`
- Uncertainty: `limen/clinical/uncertainty_analysis.py`
- Safety: `limen/safety/rules.py`, `limen/safety/governor.py`
- Orchestration: `limen/conversation/orchestrator.py`
