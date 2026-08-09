#!/usr/bin/env python3
"""PHASE 5C — benchmark completion & integrity.

Reproducible G3 local Ollama LLM benchmark orchestration.

Does NOT switch the production default model.
Does NOT use label_ground_truth in prompts.
Does NOT modify Safety Governor, RAG, or production LLM selection.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.llm.cases import BenchmarkCase, all_cases, evidence_bank
from evals.llm.failures import (
    accumulate_failure_taxonomy,
    empty_taxonomy,
    injection_metrics_from_cases,
)
from evals.llm.identity import identity_from_tags_and_show
from evals.llm.manifest import BENCHMARK_VERSION, build_manifest, manifests_compatible
from evals.llm.metrics import (
    aggregate_tokens_per_second,
    classify_placement,
    cold_load_ms_from_usage,
    display,
    tokens_per_second_ollama,
)
from evals.llm.official_dataset import discover_official_dataset, firewall_prompt
from evals.llm.preflight import G3_LOCAL_CANDIDATES, default_base_url, run_preflight
from evals.llm.prompts import (
    ADVISORY_RISK_SYSTEM,
    INTERPRETATION_SYSTEM,
    PATIENT_RESPONSE_SYSTEM,
    advisory_risk_user_prompt,
    interpretation_user_prompt,
    patient_response_user_prompt,
)
from evals.llm.resources import snapshot_resources
from evals.llm.schemas import BenchmarkAdvisoryRisk, BenchmarkInterpretation
from evals.llm.scorecard import recommend_primary_fallback
from evals.llm.scoring import (
    advisory_confusion,
    aggregate_family,
    latency_summary,
    score_advisory,
    score_interpretation,
    score_patient_response,
)

from limen.intelligence.contracts import LLMRequest, LLMResponse
from limen.intelligence.providers.ollama import (
    G3_ALLOWED_OLLAMA_MODELS,
    OllamaLLMProvider,
    is_g3_allowed_ollama_model,
)
from limen.knowledge.contracts import EvidenceChunk
from limen.safety.decision import SafetyDecision, Severity

CANDIDATES = (
    {
        "id": "llama3.2:1b",
        "family": "Llama 3.2",
        "parameter_class": "1B",
        "ollama_tags": ("llama3.2:1b",),
    },
    {
        "id": "llama3.2:3b",
        "family": "Llama 3.2",
        "parameter_class": "3B",
        "ollama_tags": ("llama3.2:3b",),
    },
    {
        "id": "phi3.5",
        "family": "Phi-3.5 Mini",
        "parameter_class": "3.8B",
        "ollama_tags": ("phi3.5", "phi3.5:latest", "phi3.5:3.8b"),
    },
)

TEMPERATURE = 0.2
MAX_TOKENS = 256
REPEATS = 3
KEEP_ALIVE_DURING = "5m"
KEEP_ALIVE_UNLOAD = 0


def _resolve_installed_tag(available: list[str], tags: tuple[str, ...]) -> str | None:
    available_l = {a.lower(): a for a in available}
    for tag in tags:
        if tag.lower() in available_l:
            return available_l[tag.lower()]
        for installed_l, original in available_l.items():
            if installed_l.startswith(f"{tag.lower()}@"):
                return original
    return None


def _safety_for(case: BenchmarkCase) -> SafetyDecision:
    severity = Severity[case.final_risk]
    return SafetyDecision(
        severity=severity,
        escalate=case.escalate or severity >= Severity.ORANGE,
        reasons=[f"benchmark_fixed:{case.final_risk}"],
    )


def _evidence_for(case: BenchmarkCase) -> list[EvidenceChunk]:
    bank = evidence_bank()
    raw = bank.get(case.evidence_mode, []) if case.evidence_mode != "none" else []
    return [
        EvidenceChunk(
            document_id=item["document_id"],
            chunk_id=item["chunk_id"],
            text=item["text"],
            source_name=item["source_name"],
            page=item.get("page"),
            retrieval_modes=["synthetic"],
        )
        for item in raw
    ]


async def _list_loaded_models(base_url: str) -> list[dict[str, Any]]:
    """GET /api/ps → models list."""
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{base_url.rstrip('/')}/api/ps")
        response.raise_for_status()
        data = response.json()
        models = data.get("models") if isinstance(data, dict) else None
        return list(models) if isinstance(models, list) else []


async def _unload_all_resident(base_url: str) -> dict[str, Any]:
    """Unload every model in /api/ps via keep_alive=0, then re-check."""
    detail: dict[str, Any] = {
        "requested": True,
        "unloaded": [],
        "errors": [],
        "resident_before": 0,
    }
    import httpx

    before = await _list_loaded_models(base_url)
    detail["resident_before"] = len(before)
    detail["resident_models_before"] = [str(m.get("name") or m.get("model") or "") for m in before]

    async with httpx.AsyncClient(timeout=60.0) as client:
        for entry in before:
            name = str(entry.get("name") or entry.get("model") or "")
            if not name:
                continue
            try:
                response = await client.post(
                    f"{base_url.rstrip('/')}/api/generate",
                    json={
                        "model": name,
                        "keep_alive": KEEP_ALIVE_UNLOAD,
                        "prompt": "",
                        "stream": False,
                    },
                )
                detail["unloaded"].append(
                    {
                        "model": name,
                        "ok": response.status_code < 400,
                        "status": response.status_code,
                    }
                )
            except Exception as exc:
                detail["errors"].append({"model": name, "error": f"{type(exc).__name__}:{exc}"})

    remaining = await _list_loaded_models(base_url)
    detail["resident_after"] = len(remaining)
    detail["resident_models_after"] = [
        str(m.get("name") or m.get("model") or "") for m in remaining
    ]
    detail["ok"] = len(remaining) == 0
    if not detail["ok"]:
        detail["limitation"] = (
            "resident_models_remain_after_unload; cold-load isolation best-effort only"
        )
    return detail


async def _placement_for_model(base_url: str, model: str) -> dict[str, Any]:
    """From /api/ps entry matching model: size, size_vram, classify_placement."""
    models = await _list_loaded_models(base_url)
    model_l = model.lower()
    entry: dict[str, Any] | None = None
    for candidate in models:
        name = str(candidate.get("name") or candidate.get("model") or "")
        if name.lower() == model_l or name.lower().startswith(f"{model_l}@"):
            entry = candidate
            break
    if entry is None:
        return {
            "placement": "UNMEASURED",
            "size_vram": "UNMEASURED",
            "size": "UNMEASURED",
            "model": model,
        }
    size_vram_raw = entry.get("size_vram")
    size_raw = entry.get("size")
    size_vram = int(size_vram_raw) if isinstance(size_vram_raw, int) else None
    size_total = int(size_raw) if isinstance(size_raw, int) else None
    placement = classify_placement(size_vram=size_vram, size_total=size_total)
    return {
        "placement": placement,
        "size_vram": size_vram if size_vram is not None else "UNMEASURED",
        "size": size_total if size_total is not None else "UNMEASURED",
        "model": entry.get("name") or entry.get("model") or model,
    }


async def _unload_model(base_url: str, model: str) -> dict[str, Any]:
    """Best-effort unload via keep_alive=0. Document limitation if imperfect."""
    detail: dict[str, Any] = {"requested": True, "ok": False, "limitation": None}
    try:
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/api/generate",
                json={
                    "model": model,
                    "keep_alive": KEEP_ALIVE_UNLOAD,
                    "prompt": "",
                    "stream": False,
                },
            )
            detail["http_status"] = response.status_code
            detail["ok"] = response.status_code < 400
            if not detail["ok"]:
                detail["limitation"] = (
                    "unload_http_error; subsequent candidate may still share VRAM/RAM"
                )
    except Exception as exc:
        detail["ok"] = False
        detail["limitation"] = f"unload_failed:{type(exc).__name__}; isolation best-effort only"
    return detail


def _collect_warm_metrics(
    response: LLMResponse,
    *,
    warm_ttfts: list[float],
    warm_gen_ms: list[float],
    warm_wall_ms: list[float],
    warm_tps_rates: list[float],
    latencies: list[float],
    collect_tps: bool = True,
) -> None:
    if response.latency_ms is not None:
        latencies.append(float(response.latency_ms))
        warm_wall_ms.append(float(response.latency_ms))
    if response.generation_ms is not None:
        warm_gen_ms.append(float(response.generation_ms))
    if response.time_to_first_token_ms is not None:
        warm_ttfts.append(float(response.time_to_first_token_ms))
    if collect_tps:
        usage = response.usage_metadata or {}
        rate = tokens_per_second_ollama(
            completion_tokens=response.completion_tokens,
            eval_duration_ns=usage.get("eval_duration_ns"),
        )
        if rate is not None:
            warm_tps_rates.append(rate)


def _finalize_family_scores(by_family: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    family_scores = {name: aggregate_family(scores) for name, scores in by_family.items() if scores}
    for fam in list(family_scores.keys()):
        if fam.endswith("__response"):
            continue
        resp_key = f"{fam}__response"
        if resp_key not in family_scores:
            continue
        fam_score = family_scores.get(fam) or {}
        resp_score = family_scores[resp_key]
        if fam_score.get("n", 0) == 0:
            del family_scores[fam]
        if resp_score.get("n", 0) == 0:
            del family_scores[resp_key]
    return family_scores


async def benchmark_candidate(
    *,
    candidate: dict[str, Any],
    model_tag: str,
    base_url: str,
    cases: list[BenchmarkCase],
    repeats: int,
    tags_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    provider = OllamaLLMProvider(
        model=model_tag,
        base_url=base_url,
        default_temperature=TEMPERATURE,
        default_max_tokens=MAX_TOKENS,
        timeout_s=300.0,
    )
    assert is_g3_allowed_ollama_model(model_tag)

    resources_before = snapshot_resources()
    show_payload: dict[str, Any] | None = None
    try:
        show_payload = await provider.show_model()
    except Exception as exc:
        show_payload = {"show_error": f"{type(exc).__name__}:{exc}"}

    identity = identity_from_tags_and_show(
        requested_tag=candidate["id"],
        resolved_tag=model_tag,
        tags_payload=tags_payload,
        show_payload=show_payload if isinstance(show_payload, dict) else None,
    )

    unload_all = await _unload_all_resident(base_url)

    # COLD MODEL LOAD — first inference after full resident unload.
    cold_ms: float | None = None
    cold_load_ms: float | None = None
    try:
        t0 = time.perf_counter()
        warm = await provider.generate_text(
            LLMRequest(
                prompt=firewall_prompt("di hola", purpose="benchmark_cold_load"),
                system=firewall_prompt("responde breve", purpose="benchmark_cold_system"),
                max_tokens=8,
            )
        )
        cold_ms = (time.perf_counter() - t0) * 1000.0
        cold_load_ms = cold_load_ms_from_usage(warm.usage_metadata, cold_ms)
    except Exception as exc:
        return {
            "candidate_id": candidate["id"],
            "model_id": candidate["id"],
            "model": model_tag,
            "resolved_tag": model_tag,
            "status": "unavailable",
            "availability": "UNAVAILABLE",
            "unavailable_reason": f"cold_load_failed:{type(exc).__name__}:{exc}",
            "identity": identity,
            "unload_all": unload_all,
        }

    runtime_placement = await _placement_for_model(base_url, model_tag)
    placement_resolved = runtime_placement.get("placement") != "UNMEASURED"

    resources_after_load = snapshot_resources()
    rss_before = resources_before.get("ollama_rss_bytes")
    rss_after = resources_after_load.get("ollama_rss_bytes")
    rss_delta = None
    if isinstance(rss_before, int) and isinstance(rss_after, int):
        rss_delta = rss_after - rss_before

    latencies: list[float] = []
    warm_ttfts: list[float] = []
    warm_gen_ms: list[float] = []
    warm_wall_ms: list[float] = []
    warm_tps_rates: list[float] = []
    tokens_in = 0
    tokens_out = 0
    token_in_known = True
    token_out_known = True
    llm_calls = 0
    errors = 0
    case_results: list[dict[str, Any]] = []
    critical_safety_failures = 0
    safety_contradictions = 0
    unsupported_claims = 0
    response_n = 0
    first_attempt_valid = 0
    schema_valid = 0
    structured_n = 0
    retries_total = 0
    taxonomy = empty_taxonomy()
    first_warm_case_done = False

    for case in cases:
        safety = _safety_for(case)
        evidence = _evidence_for(case)
        entry: dict[str, Any] = {
            "case_id": case.case_id,
            "family": case.family,
            "layer": case.layer,
            "split": case.split,
        }

        if case.family in {
            "negation",
            "colloquial_es_co",
            "noisy",
            "structured",
            "advisory_risk",
        }:
            parsed = None
            valid = False
            first_ok = False
            responses_meta: list[dict[str, Any]] = []
            try:
                parsed, responses = await provider.generate_structured_tracked(
                    LLMRequest(
                        prompt=firewall_prompt(
                            interpretation_user_prompt(case.patient_text),
                            purpose="benchmark_interpretation",
                        ),
                        system=firewall_prompt(
                            INTERPRETATION_SYSTEM, purpose="benchmark_interpretation_system"
                        ),
                        temperature=TEMPERATURE,
                        max_tokens=MAX_TOKENS,
                        metadata={"purpose": "benchmark_interpretation", "case": case.case_id},
                    ),
                    BenchmarkInterpretation,
                    max_attempts=2,
                )
                valid = True
                structured_n += 1
                schema_valid += 1
                llm_calls += len(responses)
                retries_total += max(0, len(responses) - 1)
                from limen.intelligence.structured_output import parse_structured

                try:
                    parse_structured(responses[0].text, BenchmarkInterpretation)
                    first_ok = True
                    first_attempt_valid += 1
                except Exception:
                    first_ok = False
                for response in responses:
                    _collect_warm_metrics(
                        response,
                        warm_ttfts=warm_ttfts,
                        warm_gen_ms=warm_gen_ms,
                        warm_wall_ms=warm_wall_ms,
                        warm_tps_rates=warm_tps_rates,
                        latencies=latencies,
                    )
                    if response.prompt_tokens is None:
                        token_in_known = False
                    else:
                        tokens_in += response.prompt_tokens
                    if response.completion_tokens is None:
                        token_out_known = False
                    else:
                        tokens_out += response.completion_tokens
                    responses_meta.append(
                        {
                            "latency_ms": response.latency_ms,
                            "generation_ms": response.generation_ms,
                            "ttft_ms": response.time_to_first_token_ms,
                            "input_tokens": response.prompt_tokens,
                            "output_tokens": response.completion_tokens,
                            "finish_reason": response.finish_reason,
                        }
                    )
            except Exception as exc:
                errors += 1
                llm_calls += max(1, len(responses_meta))
                structured_n += 1
                entry["interpretation_error"] = f"{type(exc).__name__}:{exc}"
            entry["interpretation"] = score_interpretation(case, parsed, valid_json=valid)
            entry["interpretation"]["llm_calls"] = len(responses_meta) or 1
            entry["interpretation"]["attempts"] = len(responses_meta) or 1
            entry["interpretation"]["first_attempt_valid"] = first_ok
            entry["interpretation"]["retry_count"] = max(0, (len(responses_meta) or 1) - 1)

        if case.family in {
            "no_evidence",
            "evidence_conflict",
            "prompt_injection",
            "colloquial_es_co",
            "structured",
        } or case.case_id.startswith("resp_"):
            try:
                response = await provider.generate_text(
                    LLMRequest(
                        prompt=firewall_prompt(
                            patient_response_user_prompt(
                                user_text=case.patient_text,
                                safety=safety,
                                evidence=evidence,
                                open_questions=[],
                            ),
                            purpose="benchmark_patient_response",
                        ),
                        system=firewall_prompt(
                            PATIENT_RESPONSE_SYSTEM, purpose="benchmark_patient_response_system"
                        ),
                        temperature=TEMPERATURE,
                        max_tokens=120,
                        metadata={"purpose": "benchmark_patient_response", "case": case.case_id},
                    )
                )
                llm_calls += 1
                _collect_warm_metrics(
                    response,
                    warm_ttfts=warm_ttfts,
                    warm_gen_ms=warm_gen_ms,
                    warm_wall_ms=warm_wall_ms,
                    warm_tps_rates=warm_tps_rates,
                    latencies=latencies,
                )
                if response.prompt_tokens is None:
                    token_in_known = False
                else:
                    tokens_in += response.prompt_tokens
                if response.completion_tokens is None:
                    token_out_known = False
                else:
                    tokens_out += response.completion_tokens
                scored = score_patient_response(case, response.text, safety)
                entry["response"] = scored
                entry["response"]["raw_preview"] = response.text[:240]
                response_n += 1
                if scored.get("contradicts_safety"):
                    safety_contradictions += 1
                    critical_safety_failures += 1
                if scored.get("unsupported_claim") or scored.get("unsupported"):
                    unsupported_claims += 1
                if scored.get("followed_injection"):
                    critical_safety_failures += 1
            except Exception as exc:
                errors += 1
                llm_calls += 1
                entry["response"] = {
                    "pass": False,
                    "error": f"{type(exc).__name__}:{exc}",
                }

        if case.expected_advisory is not None:
            parsed_adv = None
            valid_adv = False
            try:
                parsed_adv, responses = await provider.generate_structured_tracked(
                    LLMRequest(
                        prompt=firewall_prompt(
                            advisory_risk_user_prompt(case.patient_text),
                            purpose="benchmark_advisory",
                        ),
                        system=firewall_prompt(
                            ADVISORY_RISK_SYSTEM, purpose="benchmark_advisory_system"
                        ),
                        temperature=TEMPERATURE,
                        max_tokens=128,
                        metadata={"purpose": "benchmark_advisory_only", "case": case.case_id},
                    ),
                    BenchmarkAdvisoryRisk,
                    max_attempts=2,
                )
                valid_adv = True
                llm_calls += len(responses)
                retries_total += max(0, len(responses) - 1)
                for response in responses:
                    _collect_warm_metrics(
                        response,
                        warm_ttfts=warm_ttfts,
                        warm_gen_ms=warm_gen_ms,
                        warm_wall_ms=warm_wall_ms,
                        warm_tps_rates=warm_tps_rates,
                        latencies=latencies,
                    )
                    if response.prompt_tokens is None:
                        token_in_known = False
                    else:
                        tokens_in += response.prompt_tokens
                    if response.completion_tokens is None:
                        token_out_known = False
                    else:
                        tokens_out += response.completion_tokens
            except Exception as exc:
                errors += 1
                llm_calls += 1
                entry["advisory_error"] = f"{type(exc).__name__}:{exc}"
            entry["advisory"] = score_advisory(case, parsed_adv, valid_json=valid_adv)

        accumulate_failure_taxonomy(
            taxonomy,
            case_id=case.case_id,
            family=case.family,
            interpretation=entry.get("interpretation"),
            response=entry.get("response"),
            advisory=entry.get("advisory"),
        )
        case_results.append(entry)

        if not placement_resolved and not first_warm_case_done:
            runtime_placement = await _placement_for_model(base_url, model_tag)
            placement_resolved = runtime_placement.get("placement") != "UNMEASURED"
        first_warm_case_done = True

        for _ in range(max(0, repeats - 1)):
            try:
                response = await provider.generate_text(
                    LLMRequest(
                        prompt=firewall_prompt("responde: ok", purpose="benchmark_warm_repeat"),
                        system=firewall_prompt("breve", purpose="benchmark_warm_repeat_system"),
                        temperature=TEMPERATURE,
                        max_tokens=4,
                    )
                )
                llm_calls += 1
                _collect_warm_metrics(
                    response,
                    warm_ttfts=warm_ttfts,
                    warm_gen_ms=warm_gen_ms,
                    warm_wall_ms=warm_wall_ms,
                    warm_tps_rates=warm_tps_rates,
                    latencies=latencies,
                    collect_tps=False,
                )
            except Exception:
                break

    unload = await _unload_model(base_url, model_tag)
    resources_after_unload = snapshot_resources()

    by_family: dict[str, list[dict[str, Any]]] = {}
    advisory_rows: list[dict[str, Any]] = []
    for row in case_results:
        fam = row["family"]
        if "interpretation" in row:
            by_family.setdefault(fam, []).append(row["interpretation"])
        if "response" in row:
            by_family.setdefault(f"{fam}__response", []).append(row["response"])
        if isinstance(row.get("advisory"), dict) and not row["advisory"].get("skipped"):
            advisory_rows.append(row["advisory"])

    family_scores = _finalize_family_scores(by_family)
    adv = advisory_confusion(advisory_rows)
    injection = injection_metrics_from_cases(case_results)

    schema_valid_rate = (schema_valid / structured_n) if structured_n else None
    first_attempt_rate = (first_attempt_valid / structured_n) if structured_n else None
    retry_rate = (retries_total / structured_n) if structured_n else None
    unsupported_rate = (unsupported_claims / response_n) if response_n else None
    contradiction_rate = (safety_contradictions / response_n) if response_n else None

    gen_summary = latency_summary(warm_gen_ms)
    ttft_summary = latency_summary(warm_ttfts)
    wall_summary = latency_summary(warm_wall_ms)
    tps_agg = aggregate_tokens_per_second(warm_tps_rates)
    tps_value: float | str = tps_agg if tps_agg is not None else "UNMEASURED"

    return {
        "candidate_id": candidate["id"],
        "model_id": candidate["id"],
        "model": model_tag,
        "resolved_tag": model_tag,
        "family": candidate["family"],
        "parameter_class": candidate["parameter_class"],
        "g3_allowed": True,
        "status": "measured",
        "availability": "AVAILABLE",
        "identity": identity,
        "configuration": {
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "provider": "ollama",
            "base_url": base_url,
            "keep_alive_during": KEEP_ALIVE_DURING,
            "metric_label": "TEXT LLM INFERENCE METRICS",
            "voice_latency": "NOT_IMPLEMENTED",
        },
        "cold_load_ms": cold_load_ms,
        "cold_wall_ms": cold_ms,
        "unload_all": unload_all,
        "runtime_placement": runtime_placement,
        "performance": {
            "cold_load_ms": cold_load_ms,
            "warm_ttft_ms": ttft_summary,
            "warm_ttft_ms_p50": (ttft_summary or {}).get("p50_ms"),
            "warm_ttft_ms_p95": (ttft_summary or {}).get("p95_ms"),
            "generation_latency_ms": gen_summary,
            "generation_latency_ms_p50": (gen_summary or {}).get("p50_ms"),
            "generation_latency_ms_p95": (gen_summary or {}).get("p95_ms"),
            "wall_latency_ms": wall_summary,
            "tokens_per_second": tps_value,
            "tokens_per_second_basis": "ollama_eval_count_over_eval_duration_ns",
            "ttft_basis": "ollama_prompt_eval_duration_ns",
            "cold_load_basis": "ollama_load_duration_ns_or_wall_after_unload",
        },
        "injection": injection,
        "failure_taxonomy": taxonomy,
        "latency": latency_summary(latencies),
        "ttft": ttft_summary if warm_ttfts else {"n": 0, "p50_ms": None, "p95_ms": None},
        "llm_calls": llm_calls,
        "model_invocations": llm_calls,
        "error_rate": (errors / max(1, llm_calls)),
        "input_tokens": tokens_in if token_in_known else None,
        "output_tokens": tokens_out if token_out_known else None,
        "structured_output": {
            "schema_valid_rate": schema_valid_rate,
            "first_attempt_valid_rate": first_attempt_rate,
            "retry_rate": retry_rate,
            "required_fields_complete_rate": schema_valid_rate,
        },
        "structured_output_valid_rate": schema_valid_rate,
        "families": family_scores,
        "family_scores": family_scores,
        "advisory": adv,
        "advisory_risk": {
            "red_false_negatives": adv.get("red_false_negatives"),
            "confusion": adv,
            "note": "BENCHMARK ONLY — never wired into SafetyDecision",
        },
        "critical_safety_failures": critical_safety_failures,
        "safety_decision_contradiction_rate": contradiction_rate,
        "unsupported_claim_rate": unsupported_rate,
        "measured_case_count": len(case_results),
        "case_results": case_results,
        "cases": case_results,
        "unload": unload,
        "resources": {
            "rss_before_bytes": rss_before if rss_before is not None else "UNMEASURED",
            "rss_after_load_bytes": rss_after if rss_after is not None else "UNMEASURED",
            "rss_delta_bytes": rss_delta if rss_delta is not None else "UNMEASURED",
            "rss_after_unload_bytes": resources_after_unload.get("ollama_rss_bytes")
            if resources_after_unload.get("ollama_rss_bytes") is not None
            else "UNMEASURED",
        },
        "ram_rss_delta_bytes": rss_delta,
        "cost_basis": "not_available",
        "estimated_cost_usd": None,
        "local_api_cost_note": "ollama_local_no_per_request_fee",
        "production_equivalent_cost": "NOT_AVAILABLE",
        "isolation_note": (
            unload_all.get("limitation")
            or unload.get("limitation")
            or (
                "Serial unload-all→cold→warm→benchmark→unload; "
                "perfect VRAM isolation not guaranteed."
            )
        ),
        "role_hint": None,
    }


def _normalize_for_scorecard(cand: dict[str, Any]) -> dict[str, Any]:
    """Ensure scorecard extractors see consistent keys."""
    out = dict(cand)
    if out.get("availability") == "AVAILABLE":
        out["status"] = "measured"
    elif out.get("status") != "measured":
        out["status"] = "unavailable"

    fam = out.get("family_scores") or out.get("families") or {}
    mapped = dict(fam)
    if "colloquial_es_co" in fam:
        mapped["colombian_spanish"] = fam["colloquial_es_co"]
    if "noisy" in fam:
        mapped["noisy_conversation"] = fam["noisy"]
    if "evidence_conflict__response" in fam:
        mapped["evidence_grounded"] = fam["evidence_conflict__response"]
    if "structured" in fam:
        mapped["interpretation"] = fam["structured"]

    pi_resp = fam.get("prompt_injection__response")
    if isinstance(pi_resp, dict) and pi_resp.get("n", 0) > 0:
        mapped["prompt_injection"] = pi_resp
    elif "prompt_injection" in fam and fam["prompt_injection"].get("n", 0) > 0:
        mapped["prompt_injection"] = fam["prompt_injection"]

    if out.get("injection"):
        out["injection_overall_resist_rate"] = out["injection"].get("overall_resist_rate")

    out["families"] = mapped
    return out


def render_markdown(report: dict[str, Any]) -> str:
    rec = report.get("recommendation") or {}
    official = report.get("official_dataset") or {}
    commit = display((report.get("manifest") or {}).get("commit_sha") or report.get("commit_sha"))
    lines = [
        "# LLM BENCHMARK (generated) — PHASE 5C",
        "",
        f"Generated at: `{report.get('generated_at')}`",
        f"Commit: `{commit}`",
        f"Benchmark version: `{display((report.get('manifest') or {}).get('benchmark_version'))}`",
        "",
        "## SYNTHETIC CONTROL RESULTS",
        "",
        (
            "| Model | Status | Schema valid | Unsupported claim | "
            "Safety contradictions | Injection resist | P50 gen ms |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cand in report.get("candidates", []):
        so = cand.get("structured_output") or {}
        inj_block = cand.get("injection") or {}
        inj_rate = inj_block.get("overall_resist_rate")
        perf = cand.get("performance") or {}
        lines.append(
            "| {mid} | {st} | {sv} | {uc} | {sc} | {inj} | {p50} |".format(
                mid=cand.get("candidate_id"),
                st=display(cand.get("availability") or cand.get("status")),
                sv=display(so.get("schema_valid_rate", cand.get("structured_output_valid_rate"))),
                uc=display(cand.get("unsupported_claim_rate")),
                sc=display(cand.get("safety_decision_contradiction_rate")),
                inj=display(inj_rate),
                p50=display(perf.get("generation_latency_ms_p50")),
            )
        )

    lines.extend(
        [
            "",
            "## OFFICIAL DATASET RESULTS",
            "",
            (
                "Status: `"
                + str(
                    display(
                        official.get(
                            "OFFICIAL_DATASET",
                            official.get("status", "UNAVAILABLE"),
                        )
                    )
                )
                + "`"
            ),
            f"Resolved root: `{display(official.get('resolved_root'))}`",
            (f"Resolution order: `{display(official.get('resolution_order'))}`"),
            f"Files found: `{display(official.get('files_found', []))}`",
            f"Evaluation enabled: `{display(official.get('evaluation_enabled', False))}`",
            "",
            "### Dataset fingerprint",
            "",
        ]
    )
    fingerprints = official.get("fingerprints") or []
    if not fingerprints:
        lines.append("- UNMEASURED (official dataset unavailable)")
    else:
        for fp in fingerprints:
            lines.append(
                f"- **{display(fp.get('filename'))}**: "
                f"sha256=`{display(fp.get('sha256'))}` "
                f"rows=`{display(fp.get('row_count'))}` "
                f"columns=`{display(fp.get('columns'))}`"
            )
    lines.extend(
        [
            "",
            "Official metrics: **UNMEASURED** (do not treat synthetic scores as challenge scores).",
            "",
            "## RUNTIME PERFORMANCE",
            "",
            "Label: **TEXT LLM INFERENCE METRICS** (not voice).",
            "",
        ]
    )
    for cand in report.get("candidates", []):
        if cand.get("availability") != "AVAILABLE":
            continue
        perf = cand.get("performance") or {}
        placement = cand.get("runtime_placement") or {}
        lines.append(
            f"- **{cand.get('candidate_id')}**: "
            f"cold_load_ms={display(perf.get('cold_load_ms'))} "
            f"ttft_p50={display(perf.get('warm_ttft_ms_p50'))} "
            f"gen_p50={display(perf.get('generation_latency_ms_p50'))} "
            f"tok/s={display(perf.get('tokens_per_second'))} "
            f"placement={display(placement.get('placement'))} "
            f"vram={display(placement.get('size_vram'))} "
            f"RAM_delta={display(cand.get('ram_rss_delta_bytes'))} "
            f"size={display((cand.get('identity') or {}).get('artifact_size_bytes'))}"
        )

    lines.extend(["", "## SAFETY FAILURES", ""])
    any_fail = False
    for cand in report.get("candidates", []):
        fails = int(cand.get("critical_safety_failures") or 0)
        if fails:
            any_fail = True
            lines.append(f"- {cand.get('candidate_id')}: critical_safety_failures={fails}")
            for row in cand.get("case_results") or cand.get("cases") or []:
                resp = row.get("response") or {}
                if resp.get("contradicts_safety") or resp.get("followed_injection"):
                    lines.append(
                        f"  - case `{row.get('case_id')}`: "
                        f"contradicts={display(resp.get('contradicts_safety'))} "
                        f"injection={display(resp.get('followed_injection'))}"
                    )
    if not any_fail:
        lines.append("- None recorded among measured candidates (or no candidates measured).")

    lines.extend(["", "## FAILURE TAXONOMY SUMMARY", ""])
    for cand in report.get("candidates", []):
        tax = cand.get("failure_taxonomy") or {}
        if not tax:
            continue
        nonzero = {k: v for k, v in tax.items() if v}
        if not nonzero:
            lines.append(f"- {cand.get('candidate_id')}: no failures recorded")
            continue
        parts = ", ".join(f"{k}={v}" for k, v in sorted(nonzero.items()))
        lines.append(f"- {cand.get('candidate_id')}: {parts}")

    lines.extend(["", "## INJECTION RESISTANCE (patient vs evidence)", ""])
    for cand in report.get("candidates", []):
        inj = cand.get("injection") or {}
        if not inj:
            continue
        patient = inj.get("patient_side") or {}
        evidence = inj.get("evidence_side") or {}
        lines.append(
            f"- **{cand.get('candidate_id')}**: overall={display(inj.get('overall_resist_rate'))} "
            f"patient={display(patient.get('resist_rate'))} (n={display(patient.get('n'))}) "
            f"evidence={display(evidence.get('resist_rate'))} (n={display(evidence.get('n'))})"
        )

    reason_text = rec.get("rationale") or rec.get("reason") or "UNMEASURED"
    lines.extend(
        [
            "",
            "## MODEL RECOMMENDATION",
            "",
            f"STATUS: `{display(rec.get('STATUS'))}`",
            f"PRIMARY_MODEL: `{display(rec.get('PRIMARY_MODEL'))}`",
            f"FALLBACK_MODEL: `{display(rec.get('FALLBACK_MODEL'))}`",
            "",
            reason_text,
            "",
            "Methodology (fixed before scores): safety eligibility → contradictions → "
            "RED FN → unsupported claims → structured reliability → grounding → "
            "Spanish/noisy → injection → latency → memory.",
            "",
            "Production model is **NOT** switched by this report (PHASE 5.1 not started).",
            "",
            "## UNMEASURED",
            "",
            "- Voice latency: NOT_IMPLEMENTED",
            "- production_equivalent_cost: NOT_AVAILABLE",
            "- Official clean/noisy: UNMEASURED unless dataset present with evaluation enabled",
            "",
        ]
    )
    return "\n".join(lines)


def _load_completed_candidate(run_dir: Path, candidate_id: str) -> dict[str, Any] | None:
    safe = candidate_id.replace(":", "-")
    path = run_dir / f"{safe}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("availability") == "AVAILABLE" and data.get("status") == "measured":
        return data
    return None


def _attach_candidate_roles(results: list[dict[str, Any]], recommendation: dict[str, Any]) -> None:
    roles = recommendation.get("candidate_roles") or {}
    for cand in results:
        cid = str(cand.get("candidate_id") or cand.get("model_id") or "")
        if cid in roles:
            cand["role_hint"] = roles[cid]


async def async_main(args: argparse.Namespace) -> int:
    base_url = (args.base_url or default_base_url()).rstrip("/")
    cases = all_cases()
    official = discover_official_dataset()
    preflight = run_preflight(base_url=base_url)

    case_ids = [c.case_id for c in cases]
    dataset_sources = ["synthetic_control_probes"]
    if official.available:
        dataset_sources.append("official_discovered_but_eval_disabled")

    manifest = build_manifest(
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        repeats=args.repeats,
        case_ids=case_ids,
        dataset_sources=dataset_sources,
        ollama_version=preflight.ollama_version,
        candidate_models=list(G3_LOCAL_CANDIDATES),
        base_url=base_url,
        extra={
            "preflight_ready": preflight.ready_for_benchmark,
            "official_dataset": official.status,
            "benchmark_version": BENCHMARK_VERSION,
        },
    )

    run_id = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    runs_root = ROOT / "runtime" / "benchmarks" / "llm" / "runs"
    run_dir = Path(args.run_dir) if args.run_dir else runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    resume_dir: Path | None = None
    if args.resume_dir:
        resume_dir = Path(args.resume_dir)
        prior_manifest_path = resume_dir / "manifest.json"
        if prior_manifest_path.is_file():
            prior = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
            if not manifests_compatible(prior, manifest):
                print("Resume rejected: stale/incompatible prior manifest.", flush=True)
                resume_dir = None
            else:
                print(f"Resuming compatible run from {resume_dir}", flush=True)
        else:
            resume_dir = None

    tags_payload: dict[str, Any] | None = None
    available_models = list(preflight.installed_models)
    health_error: str | None = None
    if not preflight.server_ok:
        health_error = ";".join(preflight.blocking_reasons) or "ollama_unreachable"
    else:
        try:
            import httpx

            resp = httpx.get(f"{base_url}/api/tags", timeout=5.0)
            if resp.status_code == 200:
                tags_payload = resp.json()
        except Exception as exc:
            health_error = f"{type(exc).__name__}:{exc}"

    results: list[dict[str, Any]] = []
    candidates_to_run = list(CANDIDATES)
    if args.all_allowed_local:
        candidates_to_run = list(CANDIDATES)

    for candidate in candidates_to_run:
        cand_id = candidate["id"]
        if resume_dir:
            reused = _load_completed_candidate(resume_dir, cand_id)
            if reused:
                print(f"Skipping completed candidate {cand_id} (resume)", flush=True)
                results.append(reused)
                safe = cand_id.replace(":", "-")
                (run_dir / f"{safe}.json").write_text(
                    json.dumps(reused, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                continue

        if health_error:
            result = {
                "candidate_id": cand_id,
                "model_id": cand_id,
                "status": "unavailable",
                "availability": "UNAVAILABLE",
                "unavailable_reason": f"ollama_unreachable:{health_error}",
            }
            results.append(result)
            (run_dir / f"{cand_id.replace(':', '-')}.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            continue

        tag = _resolve_installed_tag(available_models, candidate["ollama_tags"])
        if tag is None:
            result = {
                "candidate_id": cand_id,
                "model_id": cand_id,
                "status": "unavailable",
                "availability": "UNAVAILABLE",
                "unavailable_reason": (
                    "model_not_installed_locally:"
                    f"tried={list(candidate['ollama_tags'])};"
                    f"available={available_models}"
                ),
            }
            results.append(result)
            (run_dir / f"{cand_id.replace(':', '-')}.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            continue

        print(f"Benchmarking {cand_id} as {tag} (serial isolation) ...", flush=True)
        try:
            result = await benchmark_candidate(
                candidate=candidate,
                model_tag=tag,
                base_url=base_url,
                cases=cases,
                repeats=args.repeats,
                tags_payload=tags_payload,
            )
        except Exception as exc:
            result = {
                "candidate_id": cand_id,
                "model_id": cand_id,
                "status": "unavailable",
                "availability": "UNAVAILABLE",
                "unavailable_reason": f"candidate_failed:{type(exc).__name__}:{exc}",
            }
            print(f"Candidate {cand_id} failed; continuing. {exc}", flush=True)

        results.append(result)
        (run_dir / f"{cand_id.replace(':', '-')}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    scorecard_inputs = [_normalize_for_scorecard(c) for c in results]
    official_red_available = bool(official.evaluation_enabled)
    recommendation = recommend_primary_fallback(
        scorecard_inputs,
        official_red_available=official_red_available,
    )
    _attach_candidate_roles(results, recommendation)

    report = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "phase": "5C",
        "commit_sha": manifest.get("commit_sha"),
        "manifest": manifest,
        "preflight": preflight.to_dict(),
        "official_dataset": official.to_dict(),
        "hardware": manifest,
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "ollama_version": preflight.ollama_version,
        "ollama_base_url": base_url,
        "g3_allowed_models": sorted(G3_ALLOWED_OLLAMA_MODELS),
        "configuration": {
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "repeats": args.repeats,
            "serial_isolation": True,
            "metric_label": "TEXT LLM INFERENCE METRICS",
        },
        "evaluation_set": {
            "source": "synthetic_control_probes",
            "official_dataset": official.status,
            "capa1_limpia": "UNMEASURED",
            "capa2_ruidosa": "UNMEASURED",
            "n_cases": len(cases),
            "ground_truth_in_prompts": False,
            "note": (
                "Official Tech Sphere dataset labels were not used as prompts. "
                "No caso_id hard-coding. Official split metrics remain UNMEASURED "
                "until the dataset is mounted offline with evaluation enabled."
            ),
        },
        "metric_methodology": {
            "latency": "monotonic wall around Ollama /api/chat; P50/P95 nearest-rank",
            "cold_vs_warm": "cold_load = first call after unload-all; warm = subsequent case calls",
            "ttft": "ollama prompt_eval_duration_ns when provided else UNMEASURED",
            "generation_latency": (
                "prefer response.generation_ms from Ollama eval_duration_ns on warm calls; "
                "wall_latency_ms tracked separately"
            ),
            "tokens_per_second": (
                "ollama eval_count / eval_duration_ns on warm inference calls only; "
                "never wall-clock estimated"
            ),
            "tokens": "ollama prompt_eval_count / eval_count; null if absent",
            "cost": "local fee none; production-equivalent NOT_AVAILABLE",
            "advisory_risk": "benchmark-only; never enters SafetyDecision",
            "voice_latency": "NOT_IMPLEMENTED",
            "scorecard": "predefined_priority_safety_over_speed",
            "placement": "Ollama /api/ps size_vram via classify_placement",
        },
        "candidates": results,
        "recommendation": recommendation,
        "run_dir": str(run_dir),
    }

    summary_path = run_dir / "summary.json"
    summary_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    out_json = Path(args.json_out)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {summary_path}")

    if args.write_docs:
        docs = Path(args.docs_out)
        docs.parent.mkdir(parents=True, exist_ok=True)
        docs.write_text(render_markdown(report), encoding="utf-8")
        print(f"Wrote {docs}")

    print("\n=== PHASE 5C comparison ===")
    for cand in results:
        inj = (cand.get("injection") or {}).get("overall_resist_rate")
        print(
            f"  {cand.get('candidate_id')}: {cand.get('availability')} "
            f"schema={(cand.get('structured_output') or {}).get('schema_valid_rate')} "
            f"contra={cand.get('safety_decision_contradiction_rate')} "
            f"injection={inj} role={cand.get('role_hint')}"
        )
    print(f"STATUS={recommendation.get('STATUS')}")
    print(f"PRIMARY_MODEL={recommendation.get('PRIMARY_MODEL')}")
    print(f"FALLBACK_MODEL={recommendation.get('FALLBACK_MODEL')}")

    if not any(c.get("availability") == "AVAILABLE" for c in results):
        print("\n=== OPERATOR ACTIONS REQUIRED ===")
        for line in preflight.operator_instructions:
            print(line)
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=None)
    parser.add_argument(
        "--json-out",
        default=str(ROOT / "runtime" / "benchmarks" / "llm" / "latest.json"),
    )
    parser.add_argument(
        "--docs-out",
        default=str(ROOT / "docs" / "LLM_BENCHMARK.generated.md"),
    )
    parser.add_argument("--write-docs", action="store_true")
    parser.add_argument("--repeats", type=int, default=REPEATS)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--resume-dir", default=None)
    parser.add_argument("--all-allowed-local", action="store_true", help="Benchmark all G3 locals")
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
