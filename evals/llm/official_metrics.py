"""Official advisory benchmark metrics (evaluation only)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from evals.llm.official_labels import NORMALIZED_LABELS, OfficialRiskLabel
from evals.llm.official_reconstruct import LAYER_CLEAN, LAYER_NOISY

PREDICTION_LABELS = ("GREEN", "YELLOW", "ORANGE", "RED")


def _safe_pred(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip().upper()
    if value in PREDICTION_LABELS:
        return value
    return None


def score_official_prediction(
    *,
    ground_truth: OfficialRiskLabel,
    predicted: str | None,
    valid_json: bool,
) -> dict[str, Any]:
    """Score one official advisory prediction."""
    pred = _safe_pred(predicted)
    if not valid_json or pred is None:
        return {
            "ground_truth": ground_truth,
            "predicted": pred,
            "exact_match": False,
            "red_false_negative": ground_truth == "RED",
            "valid_schema": False,
        }
    exact = pred == ground_truth
    red_fn = ground_truth == "RED" and pred != "RED"
    return {
        "ground_truth": ground_truth,
        "predicted": pred,
        "exact_match": exact,
        "red_false_negative": red_fn,
        "valid_schema": True,
    }


def _per_class_prf(
    labels: tuple[str, ...], tp: dict[str, int], fp: dict[str, int], fn: dict[str, int]
) -> dict[str, dict[str, float | None]]:
    out: dict[str, dict[str, float | None]] = {}
    for label in labels:
        tp_v = tp[label]
        fp_v = fp[label]
        fn_v = fn[label]
        precision = tp_v / (tp_v + fp_v) if (tp_v + fp_v) else None
        recall = tp_v / (tp_v + fn_v) if (tp_v + fn_v) else None
        if precision is not None and recall is not None and (precision + recall) > 0:
            f1 = 2 * precision * recall / (precision + recall)
        else:
            f1 = None
        out[label] = {"precision": precision, "recall": recall, "f1": f1}
    return out


def compute_official_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate accuracy, macro F1, confusion, RED FN from scored rows."""
    usable = [r for r in rows if r.get("ground_truth") in NORMALIZED_LABELS]
    if not usable:
        return {
            "n": 0,
            "accuracy": None,
            "macro_f1": None,
            "per_class": {},
            "confusion": {},
            "red_false_negatives": 0,
            "red_total": 0,
            "red_fn_rate": None,
            "red_recall": None,
        }

    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    confusion: dict[str, dict[str, int]] = {
        gt: {pred: 0 for pred in PREDICTION_LABELS} for gt in NORMALIZED_LABELS
    }
    exact_matches = 0
    red_fn = 0
    red_total = 0

    for row in usable:
        gt = str(row["ground_truth"])
        pred = _safe_pred(row.get("predicted"))
        if row.get("exact_match"):
            exact_matches += 1
        if gt == "RED":
            red_total += 1
            if row.get("red_false_negative"):
                red_fn += 1
        if pred is None:
            fn[gt] += 1
            continue
        if gt in confusion and pred in confusion[gt]:
            confusion[gt][pred] += 1
        if pred == gt:
            tp[gt] += 1
        else:
            fp[pred] += 1
            fn[gt] += 1

    per_class = _per_class_prf(NORMALIZED_LABELS, tp, fp, fn)
    f1_values = [v["f1"] for v in per_class.values() if v["f1"] is not None]
    macro_f1 = sum(f1_values) / len(f1_values) if f1_values else None
    red_recall = (
        (red_total - red_fn) / red_total if red_total else None
    )

    return {
        "n": len(usable),
        "accuracy": exact_matches / len(usable),
        "macro_f1": macro_f1,
        "per_class": per_class,
        "confusion": confusion,
        "red_false_negatives": red_fn,
        "red_total": red_total,
        "red_fn_rate": (red_fn / red_total) if red_total else None,
        "red_recall": red_recall,
    }


def compute_layer_metrics(
    rows: list[dict[str, Any]], *, layer: str
) -> dict[str, Any]:
    subset = [r for r in rows if r.get("layer") == layer]
    metrics = compute_official_metrics(subset)
    metrics["layer"] = layer
    return metrics


def compute_degradation(
    clean_metrics: dict[str, Any], noisy_metrics: dict[str, Any]
) -> dict[str, Any]:
    """Clean → noisy degradation (positive = worse on noisy)."""
    def delta(key: str) -> float | None:
        a = clean_metrics.get(key)
        b = noisy_metrics.get(key)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return float(a) - float(b)
        return None

    clean_red_fn = clean_metrics.get("red_false_negatives")
    noisy_red_fn = noisy_metrics.get("red_false_negatives")
    red_fn_delta = None
    if isinstance(clean_red_fn, int) and isinstance(noisy_red_fn, int):
        red_fn_delta = noisy_red_fn - clean_red_fn

    return {
        "accuracy_delta_clean_minus_noisy": delta("accuracy"),
        "macro_f1_delta_clean_minus_noisy": delta("macro_f1"),
        "red_fn_delta_noisy_minus_clean": red_fn_delta,
        "clean_layer": LAYER_CLEAN,
        "noisy_layer": LAYER_NOISY,
    }


def summarize_official_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    overall = compute_official_metrics(rows)
    clean = compute_layer_metrics(rows, layer=LAYER_CLEAN)
    noisy = compute_layer_metrics(rows, layer=LAYER_NOISY)
    return {
        "overall": overall,
        "clean": clean,
        "noisy": noisy,
        "degradation": compute_degradation(clean, noisy),
    }
