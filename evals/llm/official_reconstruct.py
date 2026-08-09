"""Reconstruct official conversation cases for benchmark inference."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from evals.llm.official_labels import normalize_official_label
from evals.llm.official_load import (
    MODEL_ALLOWED_CLINICAL_FIELDS,
    LoadedOfficialTables,
)

LAYER_CLEAN = "capa1_limpia"
LAYER_NOISY = "capa2_ruidosa"
EXPECTED_LAYERS = (LAYER_CLEAN, LAYER_NOISY)


@dataclass
class OfficialConversationCase:
    case_id: str
    patient_id: str
    layer: str
    ordered_turns: list[dict[str, Any]]
    known_clinical_profile: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OfficialEvaluationTruth:
    case_id: str
    layer: str
    label_raw: str
    label_normalized: str
    trajectory_truth: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReconstructedOfficialDataset:
    conversations: list[OfficialConversationCase]
    truths: list[OfficialEvaluationTruth]
    stats: dict[str, Any]
    validation_errors: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.validation_errors


def _clinical_profile_for_patient(
    profiles: list[dict[str, Any]], patient_id: str
) -> dict[str, Any]:
    for row in profiles:
        if str(row.get("paciente_id") or "") == patient_id:
            return {
                key: row.get(key)
                for key in MODEL_ALLOWED_CLINICAL_FIELDS
                if row.get(key) is not None
            }
    return {}


def _trajectory_for_case(
    trajectories: list[dict[str, Any]], case_id: str
) -> dict[str, Any] | None:
    expected_tray_id = case_id.removeprefix("caso_")
    for row in trajectories:
        tray_id = str(row.get("trayectoria_id") or "")
        if tray_id == expected_tray_id or f"caso_{tray_id}" == case_id:
            return dict(row)
    return None


def _turn_sort_key(row: dict[str, Any]) -> tuple[int, int]:
    turn_idx = row.get("turno_idx")
    dialogo_id = row.get("dialogo_id")
    try:
        turn_num = int(turn_idx)
    except (TypeError, ValueError):
        turn_num = 0
    try:
        dialogo_num = int(dialogo_id) if dialogo_id is not None else 0
    except (TypeError, ValueError):
        dialogo_num = 0
    return turn_num, dialogo_num


def reconstruct_official_dataset(tables: LoadedOfficialTables) -> ReconstructedOfficialDataset:
    """Build ~320 conversation cases (160 cases × clean/noisy layers)."""
    errors: list[str] = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    labels_by_case: dict[str, str] = {}

    for row in tables.turns:
        case_id = str(row.get("caso_id") or "").strip()
        layer = str(row.get("capa") or "").strip()
        patient_id = str(row.get("paciente_id") or "").strip()
        if not case_id or not layer or not patient_id:
            errors.append(f"turn_missing_keys:{row.get('dialogo_id')}")
            continue
        grouped[(case_id, layer)].append(row)
        raw_label = row.get("label_ground_truth")
        if raw_label is None:
            errors.append(f"missing_label:{case_id}")
            continue
        raw_s = str(raw_label).strip()
        if case_id not in labels_by_case:
            labels_by_case[case_id] = raw_s
        elif labels_by_case[case_id] != raw_s:
            errors.append(f"inconsistent_label:{case_id}")

    conversations: list[OfficialConversationCase] = []
    truths: list[OfficialEvaluationTruth] = []

    for (case_id, layer), rows in sorted(grouped.items(), key=lambda item: item[0]):
        rows_sorted = sorted(rows, key=_turn_sort_key)
        ordered_turns = [
            {
                "turno_idx": row.get("turno_idx"),
                "hablante": row.get("hablante"),
                "texto": row.get("texto"),
            }
            for row in rows_sorted
        ]
        patient_id = str(rows_sorted[0].get("paciente_id") or "")
        profile = _clinical_profile_for_patient(tables.clinical_profiles, patient_id)
        if not profile:
            errors.append(f"missing_clinical_profile:{patient_id}:{case_id}")

        trajectory = _trajectory_for_case(tables.trajectories, case_id)
        if trajectory is None:
            errors.append(f"missing_trajectory:{case_id}")

        raw_label = labels_by_case.get(case_id, "")
        try:
            normalized = normalize_official_label(raw_label)
        except ValueError as exc:
            errors.append(f"bad_label:{case_id}:{exc}")
            normalized = "GREEN"

        conversations.append(
            OfficialConversationCase(
                case_id=case_id,
                patient_id=patient_id,
                layer=layer,
                ordered_turns=ordered_turns,
                known_clinical_profile=profile,
            )
        )
        truths.append(
            OfficialEvaluationTruth(
                case_id=case_id,
                layer=layer,
                label_raw=raw_label,
                label_normalized=normalized,
                trajectory_truth=trajectory or {},
            )
        )

    case_ids = {c.case_id for c in conversations}
    layer_counts = Counter(c.layer for c in conversations)
    label_dist = Counter(labels_by_case.values())

    if len(case_ids) != 160:
        errors.append(f"expected_160_cases_found_{len(case_ids)}")
    for layer in EXPECTED_LAYERS:
        if layer_counts.get(layer, 0) != 160:
            errors.append(f"expected_160_{layer}_found_{layer_counts.get(layer, 0)}")

    stats = {
        "turn_count": len(tables.turns),
        "conversation_count": len(conversations),
        "unique_case_ids": len(case_ids),
        "layer_counts": dict(layer_counts),
        "label_distribution_by_case": dict(label_dist),
        "clinical_profile_rows": len(tables.clinical_profiles),
        "trajectory_rows": len(tables.trajectories),
        "demographics_rows": len(tables.patient_demographics),
    }
    return ReconstructedOfficialDataset(
        conversations=conversations,
        truths=truths,
        stats=stats,
        validation_errors=errors,
    )


def build_transcript(conversation: OfficialConversationCase) -> str:
    """Render hablante+texto transcript for advisory prompt (no GT)."""
    lines: list[str] = []
    for turn in conversation.ordered_turns:
        speaker = str(turn.get("hablante") or "desconocido")
        text = str(turn.get("texto") or "").strip()
        if not text:
            continue
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)
