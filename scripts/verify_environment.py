#!/usr/bin/env python3
"""Verify local environment for LIMEN foundation + RAG runtime readiness.

Lightweight by default: does NOT download or load the embedding model.
Pass ``--full`` to initialize the configured embedding provider (may download).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from limen.config.settings import get_settings
from limen.intelligence.providers import build_llm_provider
from limen.knowledge.embeddings import (
    EXPECTED_E5_DIMENSIONS,
    build_embedding_provider,
    local_model_available,
    resolve_embedding_model_name,
)
from limen.persistence.database import Database
from limen.voice.stt import build_stt_provider
from limen.voice.tts import build_tts_provider


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _sentence_transformers_status() -> tuple[bool, str]:
    try:
        import sentence_transformers

        return True, getattr(sentence_transformers, "__version__", "unknown")
    except ImportError:
        return False, "not installed"


def _torch_status() -> tuple[str, str]:
    try:
        import torch

        version = getattr(torch, "__version__", "unknown")
        cuda = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
        mode = "GPU (CUDA available)" if cuda else "CPU"
        return version, mode
    except ImportError:
        return "not installed", "N/A"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full",
        action="store_true",
        help="Load embedding provider (may download model weights)",
    )
    args = parser.parse_args()

    settings = get_settings()
    settings.ensure_runtime_dirs()
    errors: list[str] = []
    warnings: list[str] = []

    try:
        build_llm_provider(settings)
        build_stt_provider(settings)
        build_tts_provider(settings)
    except ValueError as exc:
        errors.append(str(exc))

    # Factory construction for stub is always cheap; for ST we only construct
    # without loading unless --full.
    try:
        if settings.embedding_provider.lower().strip() == "stub" or not args.full:
            # Validate provider name / path policy without loading weights.
            if settings.embedding_provider.lower().strip() != "stub":
                resolve_embedding_model_name(settings)
            else:
                build_embedding_provider(settings)
        else:
            provider = build_embedding_provider(settings)
            dims = provider.dimensions
            if (
                dims != EXPECTED_E5_DIMENSIONS
                and "e5" in resolve_embedding_model_name(settings).lower()
            ):
                errors.append(
                    f"expected E5 embedding dimension {EXPECTED_E5_DIMENSIONS}, got {dims}"
                )
    except (ValueError, RuntimeError) as exc:
        errors.append(str(exc))

    # Probe schema on a disposable DB so a stale local runtime/db does not
    # fail environment verification (operators re-bootstrap when needed).
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        probe_db = Database(Path(tmp) / "env_probe.db")
        probe_db.initialize()
        health = probe_db.health()
        probe_db.close()
    if health.get("database") != "ok":
        errors.append("database health failed")

    if not _writable(settings.database_path.parent):
        errors.append(f"DATABASE_PATH parent not writable: {settings.database_path.parent}")

    required = [
        ROOT / "ARCHITECTURE.md",
        ROOT / "AGENTS.md",
        ROOT / "apps" / "api" / "main.py",
        ROOT / "apps" / "web" / "package.json",
        ROOT / "BACKEND.md",
        ROOT / "FRONTEND.md",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")

    st_ok, st_ver = _sentence_transformers_status()
    torch_ver, torch_mode = _torch_status()
    provider_name = settings.embedding_provider
    try:
        model_ref = resolve_embedding_model_name(settings)
    except RuntimeError as exc:
        model_ref = f"UNRESOLVED ({exc})"
        if provider_name.lower().strip() != "stub":
            errors.append(str(exc))

    local_ok = local_model_available(settings)
    vector_writable = _writable(settings.vector_path)

    if provider_name.lower().strip() in {"sentence-transformers", "st", "local"}:
        if not st_ok:
            errors.append(
                "EMBEDDING_PROVIDER requires sentence-transformers; "
                "run `make bootstrap` or `python scripts/install_embeddings_cpu.py`"
            )
        if torch_ver == "not installed":
            errors.append(
                "torch is not installed; run `python scripts/install_embeddings_cpu.py` "
                "(CPU-first index)"
            )
        if not local_ok and not args.full:
            warnings.append(
                "local model cache not configured; first real load will use "
                f"Hugging Face id {model_ref!r} (set EMBEDDING_MODEL_PATH to avoid Hub)"
            )

    if not vector_writable:
        errors.append(f"VECTOR_PATH not writable: {settings.vector_path}")

    if errors:
        print("Environment verification FAILED:")
        for err in errors:
            print(f"  - {err}")
        _print_report(
            settings=settings,
            provider_name=provider_name,
            model_ref=model_ref,
            local_ok=local_ok,
            st_ok=st_ok,
            st_ver=st_ver,
            torch_ver=torch_ver,
            torch_mode=torch_mode,
            vector_writable=vector_writable,
            full=args.full,
        )
        return 1

    print("Environment verification OK")
    _print_report(
        settings=settings,
        provider_name=provider_name,
        model_ref=model_ref,
        local_ok=local_ok,
        st_ok=st_ok,
        st_ver=st_ver,
        torch_ver=torch_ver,
        torch_mode=torch_mode,
        vector_writable=vector_writable,
        full=args.full,
    )
    for warn in warnings:
        print(f"  warning: {warn}")
    return 0


def _print_report(
    *,
    settings: object,
    provider_name: str,
    model_ref: str,
    local_ok: bool,
    st_ok: bool,
    st_ver: str,
    torch_ver: str,
    torch_mode: str,
    vector_writable: bool,
    full: bool,
) -> None:
    from limen.config.settings import ApplicationSettings

    assert isinstance(settings, ApplicationSettings)
    print(f"  LLM: {settings.llm_provider}/{settings.llm_model}")
    print(f"  STT: {settings.stt_provider}/{settings.stt_model}")
    print(f"  TTS: {settings.tts_provider}/{settings.tts_model} voice={settings.tts_voice}")
    print(f"  DB:  {settings.database_path}")
    print(f"  embedding_provider: {provider_name}")
    print(f"  embedding_model (resolved): {model_ref}")
    print(f"  embedding_model_path: {settings.embedding_model_path or '(unset)'}")
    print(f"  local_model_available: {local_ok}")
    print(f"  sentence-transformers: {'yes ' + st_ver if st_ok else 'no'}")
    print(f"  torch: {torch_ver}")
    print(f"  torch_runtime_mode: {torch_mode}")
    print(f"  vector_path: {settings.vector_path}")
    print(f"  vector_path_writable: {vector_writable}")
    print(f"  expected_e5_dimensions: {EXPECTED_E5_DIMENSIONS}")
    print(f"  full_model_load: {full}")


if __name__ == "__main__":
    raise SystemExit(main())
