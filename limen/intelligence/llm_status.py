"""Observable LLM runtime status (degraded mode without crashing the app)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class LlmRuntimeStatus:
    """Process-level LLM reachability — not a clinical decision authority."""

    configured_provider: str = "stub"
    configured_model: str = "stub-model"
    base_url: str | None = None
    reachable: bool | None = None
    degraded_mode: bool = False
    last_provider_error: str | None = None
    last_checked_at: str | None = None
    selected_model_available: bool | None = None
    notes: list[str] = field(default_factory=list)

    def mark_ok(self, *, selected_available: bool | None = None) -> None:
        self.reachable = True
        self.degraded_mode = False
        self.last_provider_error = None
        self.selected_model_available = selected_available
        self.last_checked_at = datetime.now(tz=UTC).isoformat()

    def mark_degraded(self, error: str, *, note: str | None = None) -> None:
        self.reachable = False
        self.degraded_mode = True
        self.last_provider_error = error[:500]
        self.last_checked_at = datetime.now(tz=UTC).isoformat()
        if note:
            self.notes.append(note)

    def mark_provider_error(self, error: str) -> None:
        """Record a turn-time failure without necessarily flipping degraded forever."""
        self.last_provider_error = error[:500]
        self.last_checked_at = datetime.now(tz=UTC).isoformat()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "configured_provider": self.configured_provider,
            "configured_model": self.configured_model,
            "base_url": self.base_url,
            "reachable": self.reachable,
            "degraded_mode": self.degraded_mode,
            "last_provider_error": self.last_provider_error,
            "last_checked_at": self.last_checked_at,
            "selected_model_available": self.selected_model_available,
            "notes": list(self.notes),
        }


_STATUS = LlmRuntimeStatus()


def get_llm_runtime_status() -> LlmRuntimeStatus:
    return _STATUS


def reset_llm_runtime_status_for_tests() -> None:
    global _STATUS
    _STATUS = LlmRuntimeStatus()


async def probe_llm_runtime(settings: Any, provider: Any | None = None) -> LlmRuntimeStatus:
    """Probe configured provider at startup. Never raises — sets degraded mode."""
    status = get_llm_runtime_status()
    status.configured_provider = str(getattr(settings, "llm_provider", "stub"))
    status.configured_model = str(getattr(settings, "llm_model", "stub-model"))
    status.base_url = str(getattr(settings, "llm_base_url", "") or "") or None
    status.notes.clear()

    provider_name = status.configured_provider.lower().strip()
    if provider_name == "stub":
        status.mark_ok(selected_available=True)
        status.notes.append("stub_provider_always_reachable")
        return status

    if provider_name != "ollama":
        status.mark_degraded(
            f"unsupported_provider:{provider_name}",
            note="unknown_provider_treated_as_degraded",
        )
        return status

    health_fn = getattr(provider, "health", None)
    if health_fn is None:
        status.mark_degraded("ollama_provider_missing_health", note="no_health_hook")
        return status

    try:
        payload = await health_fn()
        selected = bool(payload.get("selected_available"))
        if not payload.get("ok"):
            status.mark_degraded("ollama_health_not_ok", note="health_returned_not_ok")
            return status
        if not selected:
            status.mark_degraded(
                f"model_not_available:{status.configured_model}",
                note="configured_model_missing_on_ollama",
            )
            # Still mark reachable endpoint but degraded for generation.
            status.reachable = True
            return status
        status.mark_ok(selected_available=True)
        status.base_url = str(payload.get("base_url") or status.base_url)
        return status
    except Exception as exc:  # noqa: BLE001 — startup must not crash
        status.mark_degraded(f"{type(exc).__name__}:{exc}", note="ollama_unreachable")
        return status
