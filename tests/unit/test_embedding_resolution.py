"""Unit tests for embedding model resolution (no Hub download)."""

from __future__ import annotations

from pathlib import Path

import pytest

from limen.config.settings import ApplicationSettings
from limen.knowledge.embeddings import (
    CANONICAL_E5_MODEL_ID,
    local_model_available,
    local_model_dir_usable,
    resolve_embedding_model_name,
)


def test_resolve_defaults_to_canonical_hf_id() -> None:
    settings = ApplicationSettings(
        EMBEDDING_PROVIDER="sentence-transformers",
        EMBEDDING_MODEL="intfloat/multilingual-e5-small",
        EMBEDDING_MODEL_PATH="",
    )
    assert resolve_embedding_model_name(settings) == CANONICAL_E5_MODEL_ID
    assert local_model_available(settings) is False


def test_resolve_prefers_configured_local_path(tmp_path: Path) -> None:
    model_dir = tmp_path / "multilingual-e5-small"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "model.safetensors").write_bytes(b"x" * 2000)

    settings = ApplicationSettings(
        EMBEDDING_PROVIDER="sentence-transformers",
        EMBEDDING_MODEL="intfloat/multilingual-e5-small",
        EMBEDDING_MODEL_PATH=str(model_dir),
    )
    assert resolve_embedding_model_name(settings) == str(model_dir.resolve())
    assert local_model_available(settings) is True


def test_resolve_rejects_bad_model_path(tmp_path: Path) -> None:
    bad = tmp_path / "empty"
    bad.mkdir()
    settings = ApplicationSettings(
        EMBEDDING_PROVIDER="sentence-transformers",
        EMBEDDING_MODEL="intfloat/multilingual-e5-small",
        EMBEDDING_MODEL_PATH=str(bad),
    )
    with pytest.raises(RuntimeError, match="EMBEDDING_MODEL_PATH"):
        resolve_embedding_model_name(settings)


def test_resolve_accepts_embedding_model_as_local_dir(tmp_path: Path) -> None:
    model_dir = tmp_path / "local-e5"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "pytorch_model.bin").write_bytes(b"x" * 2000)
    settings = ApplicationSettings(
        EMBEDDING_PROVIDER="sentence-transformers",
        EMBEDDING_MODEL=str(model_dir),
        EMBEDDING_MODEL_PATH="",
    )
    assert resolve_embedding_model_name(settings) == str(model_dir.resolve())


def test_local_model_dir_usable_false_for_missing(tmp_path: Path) -> None:
    assert local_model_dir_usable(tmp_path / "nope") is False
