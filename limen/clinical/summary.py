"""Structured call summary builders — Planned beyond foundation."""

from limen.clinical.state import ClinicalState


def summarize_state(state: ClinicalState) -> str:
    if not state.findings:
        return "No clinical findings recorded."
    parts = [f"{f.name}:{f.certainty.value}" for f in state.findings]
    return "; ".join(parts)
