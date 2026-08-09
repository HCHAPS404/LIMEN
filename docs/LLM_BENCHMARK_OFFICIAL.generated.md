# LLM Benchmark — Official Dataset (generated) — PHASE 5C.2

Generated at: `2026-08-08T22:37:04.017492+00:00`
Benchmark version: `5C.2.1`
Dataset SHA256: `ddae3afdc76fd94b6c5a1ea6af0b29ebecbd9d6c1d816624e7811899fbae038f`

## Overall official results

| Model | Accuracy | Macro F1 | GREEN R | YELLOW R | RED R | RED FN | Schema valid |
| --- | --- | --- | --- | --- | --- | --- | --- |
| llama3.2:1b | 0.3 | 0.3029935145841986 | 0.2682926829268293 | 0.6 | 0.0 | 24 | 1.0 |
| llama3.2:3b | 0.2 | 0.19667580982236155 | 0.06097560975609756 | 0.98 | 0.0 | 24 | 0.990625 |
| phi3.5 | 0.409375 | 0.444805404368153 | 0.2967479674796748 | 0.98 | 0.375 | 15 | 0.9875 |

## Clean / Noisy / Degradation

### llama3.2:1b
- clean macro F1: `0.27142857142857146` accuracy=`0.26875` RED FN=`12`
- noisy macro F1: `0.33461390703034954` accuracy=`0.33125` RED FN=`12`
- degradation: `{'accuracy_delta_clean_minus_noisy': -0.0625, 'macro_f1_delta_clean_minus_noisy': -0.06318533560177808, 'red_fn_delta_noisy_minus_clean': 0, 'clean_layer': 'capa1_limpia', 'noisy_layer': 'capa2_ruidosa'}`

### llama3.2:3b
- clean macro F1: `0.21391629362423398` accuracy=`0.2125` RED FN=`12`
- noisy macro F1: `0.17872730446927373` accuracy=`0.1875` RED FN=`12`
- degradation: `{'accuracy_delta_clean_minus_noisy': 0.024999999999999994, 'macro_f1_delta_clean_minus_noisy': 0.03518898915496024, 'red_fn_delta_noisy_minus_clean': 0, 'clean_layer': 'capa1_limpia', 'noisy_layer': 'capa2_ruidosa'}`

### phi3.5
- clean macro F1: `0.49480534548407845` accuracy=`0.4625` RED FN=`7`
- noisy macro F1: `0.39233987741503107` accuracy=`0.35625` RED FN=`8`
- degradation: `{'accuracy_delta_clean_minus_noisy': 0.10625000000000001, 'macro_f1_delta_clean_minus_noisy': 0.10246546806904738, 'red_fn_delta_noisy_minus_clean': 1, 'clean_layer': 'capa1_limpia', 'noisy_layer': 'capa2_ruidosa'}`


## RED false-negative breakdown

- **llama3.2:1b**: count=24/24 rate=1.0 →GREEN=7 →YELLOW=17 →ORANGE=0 invalid=0
- **llama3.2:3b**: count=24/24 rate=1.0 →GREEN=0 →YELLOW=24 →ORANGE=0 invalid=0
- **phi3.5**: count=15/24 rate=0.625 →GREEN=0 →YELLOW=15 →ORANGE=0 invalid=0

## Selection

- STATUS: `DEFINITIVE`
- PRIMARY: `phi3.5`
- FALLBACK: `llama3.2:1b`

STATUS=DEFINITIVE
PRIMARY=phi3.5 selected because:
- G3 eligible: True
- critical_safety_failures: 0
- safety_decision_contradiction_rate: 0.0000
- synthetic advisory RED FN count: 0
- official RED FN: 15
- unsupported_claim_rate: 0.0000
- schema_valid_rate: 0.9875
- evidence_grounding_pass_rate: UNMEASURED
- colombian_spanish_pass_rate: UNMEASURED
- noisy_pass_rate: UNMEASURED
- injection_resist_rate: 1.0000
- warm_latency_p50_ms: 9.2160 (lower priority than safety/quality)
FALLBACK=llama3.2:1b because:
- schema_valid_rate: 1.0000
- injection_resist_rate: 1.0000
- warm_latency_p50_ms: 6.0840
- ranked next among non-disqualified G3 candidates under the same scorecard

Synthetic-only report remains in `docs/LLM_BENCHMARK.generated.md`.
Production LLM default is NOT switched (PHASE 5.1 not started).

