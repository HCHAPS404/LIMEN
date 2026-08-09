# LLM BENCHMARK (generated) — PHASE 5C

Generated at: `2026-08-08T07:50:46.705236+00:00`
Commit: `9fa4b8f56cb45336d86fe47d7aaa63c22df9b301`
Benchmark version: `5C.1`

## SYNTHETIC CONTROL RESULTS

| Model | Status | Schema valid | Unsupported claim | Safety contradictions | Injection resist | P50 gen ms |
| --- | --- | --- | --- | --- | --- | --- |
| llama3.2:1b | AVAILABLE | 0.0 | 0.0 | 0.0 | 1.0 | 6.025 |
| llama3.2:3b | AVAILABLE | 0.8421052631578947 | 0.0 | 0.0 | 1.0 | 26.839 |
| phi3.5 | AVAILABLE | 0.7894736842105263 | 0.0 | 0.0 | 1.0 | 24.562 |

## OFFICIAL DATASET RESULTS

Status: `UNAVAILABLE`
Resolved root: `UNMEASURED`
Resolution order: `['./dataset/', './data/challenge/', 'unavailable']`
Files found: `[]`
Evaluation enabled: `False`

### Dataset fingerprint

- UNMEASURED (official dataset unavailable)

Official metrics: **UNMEASURED** (do not treat synthetic scores as challenge scores).

## RUNTIME PERFORMANCE

Label: **TEXT LLM INFERENCE METRICS** (not voice).

- **llama3.2:1b**: cold_load_ms=5660.032437 ttft_p50=6.084 gen_p50=6.025 tok/s=192.85422500600012 placement=GPU vram=1514584145 RAM_delta=777654272 size=1321098329
- **llama3.2:3b**: cold_load_ms=5159.650908 ttft_p50=9.676 gen_p50=26.839 tok/s=122.4119187347059 placement=GPU vram=2554708622 RAM_delta=816988160 size=2019393189
- **phi3.5**: cold_load_ms=5485.714661 ttft_p50=9.216 gen_p50=24.562 tok/s=119.27311470322977 placement=GPU vram=3797764013 RAM_delta=486711296 size=2176178843

## SAFETY FAILURES

- None recorded among measured candidates (or no candidates measured).

## FAILURE TAXONOMY SUMMARY

- llama3.2:1b: advisory_red_false_negative=3, invalid_schema=19
- llama3.2:3b: advisory_red_false_negative=3, invalid_schema=3, negation_error=1
- phi3.5: advisory_red_false_negative=3, invalid_schema=4, negation_error=3

## INJECTION RESISTANCE (patient vs evidence)

- **llama3.2:1b**: overall=1.0 patient=1.0 (n=1) evidence=1.0 (n=1)
- **llama3.2:3b**: overall=1.0 patient=1.0 (n=1) evidence=1.0 (n=1)
- **phi3.5**: overall=1.0 patient=1.0 (n=1) evidence=1.0 (n=1)

## MODEL RECOMMENDATION

STATUS: `PROVISIONAL`
PRIMARY_MODEL: `llama3.2:3b`
FALLBACK_MODEL: `phi3.5`

STATUS=PROVISIONAL
PRIMARY=llama3.2:3b selected because:
- G3 eligible: True
- critical_safety_failures: 0
- safety_decision_contradiction_rate: 0.0000
- synthetic advisory RED FN count: 0
- official RED FN: UNMEASURED (official dataset unavailable)
- unsupported_claim_rate: 0.0000
- schema_valid_rate: 0.8421
- evidence_grounding_pass_rate: 1.0000
- colombian_spanish_pass_rate: 0.7500
- noisy_pass_rate: 0.6667
- injection_resist_rate: 1.0000
- warm_latency_p50_ms: 9.6760 (lower priority than safety/quality)
FALLBACK=phi3.5 because:
- schema_valid_rate: 0.7895
- injection_resist_rate: 1.0000
- warm_latency_p50_ms: 9.2160
- ranked next among non-disqualified G3 candidates under the same scorecard
Limitation: official-dataset RED false negatives are UNMEASURED; selection is provisional pending official evaluation or explicit acceptance.

Methodology (fixed before scores): safety eligibility → contradictions → RED FN → unsupported claims → structured reliability → grounding → Spanish/noisy → injection → latency → memory.

Production model is **NOT** switched by this report (PHASE 5.1 not started).

## UNMEASURED

- Voice latency: NOT_IMPLEMENTED
- production_equivalent_cost: NOT_AVAILABLE
- Official clean/noisy: UNMEASURED unless dataset present with evaluation enabled
