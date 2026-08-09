"""Normalize Ollama model identity fields without guessing."""

from __future__ import annotations

from typing import Any

NOT_AVAILABLE = "NOT_AVAILABLE"
UNMEASURED = "UNMEASURED"


def identity_from_tags_and_show(
    *,
    requested_tag: str,
    resolved_tag: str,
    tags_payload: dict[str, Any] | list[Any] | None,
    show_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Record only what Ollama exposes; otherwise UNMEASURED / NOT_AVAILABLE."""
    digest: str | None = None
    size_bytes: int | None = None
    quantization: str | None = None
    parameter_size: str | None = None
    family: str | None = None
    context_length: int | None = None

    # /api/tags entries often include digest + size.
    models: list[Any] = []
    if isinstance(tags_payload, dict):
        models = list(tags_payload.get("models") or [])
    elif isinstance(tags_payload, list):
        models = tags_payload
    for item in models:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if name.lower() != resolved_tag.lower() and not name.lower().startswith(
            f"{resolved_tag.lower()}"
        ):
            continue
        if item.get("digest"):
            digest = str(item["digest"])
        if isinstance(item.get("size"), int):
            size_bytes = int(item["size"])
        details = item.get("details") if isinstance(item.get("details"), dict) else {}
        if details.get("quantization_level") is not None:
            quantization = str(details["quantization_level"])
        if details.get("parameter_size") is not None:
            parameter_size = str(details["parameter_size"])
        if details.get("family") is not None:
            family = str(details["family"])

    show = show_payload if isinstance(show_payload, dict) else {}
    details = show.get("details") if isinstance(show.get("details"), dict) else {}
    if details.get("quantization_level") is not None:
        quantization = str(details["quantization_level"])
    if details.get("parameter_size") is not None:
        parameter_size = str(details["parameter_size"])
    if details.get("family") is not None:
        family = str(details["family"])
    if isinstance(show.get("size"), int):
        size_bytes = int(show["size"])
    for key in ("digest", "model_digest", "sha256"):
        if show.get(key):
            digest = str(show[key])
            break
    model_info = show.get("model_info")
    if isinstance(model_info, dict):
        for key, value in model_info.items():
            kl = str(key).lower()
            if "context" in kl and isinstance(value, (int, float)):
                context_length = int(value)
            if digest is None and "digest" in kl and value:
                digest = str(value)

    return {
        "requested_tag": requested_tag,
        "resolved_model": resolved_tag,
        "digest": digest if digest else UNMEASURED,
        "artifact_size_bytes": size_bytes if size_bytes is not None else UNMEASURED,
        "quantization": quantization if quantization else UNMEASURED,
        "parameter_size": parameter_size if parameter_size else UNMEASURED,
        "family": family if family else UNMEASURED,
        "context_length": context_length if context_length is not None else UNMEASURED,
    }
