"""Official challenge label normalization (EVALUATION ONLY)."""

from __future__ import annotations

from typing import Literal

OfficialRiskLabel = Literal["GREEN", "YELLOW", "RED"]

RAW_TO_NORMALIZED: dict[str, OfficialRiskLabel] = {
    "verde": "GREEN",
    "green": "GREEN",
    "amarillo": "YELLOW",
    "yellow": "YELLOW",
    "rojo": "RED",
    "red": "RED",
}

NORMALIZED_LABELS: tuple[OfficialRiskLabel, ...] = ("GREEN", "YELLOW", "RED")


def normalize_official_label(raw: str | None) -> OfficialRiskLabel:
    """Map official Spanish labels to GREEN/YELLOW/RED."""
    if raw is None:
        raise ValueError("label_ground_truth is missing")
    key = str(raw).strip().lower()
    if key not in RAW_TO_NORMALIZED:
        raise ValueError(f"unsupported official label: {raw!r}")
    return RAW_TO_NORMALIZED[key]


def is_red_label(raw: str | None) -> bool:
    return normalize_official_label(raw) == "RED"
