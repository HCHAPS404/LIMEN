"""Embedding provider stubs, adapters, and factory."""

from __future__ import annotations

import threading
from pathlib import Path

from limen.config.settings import ApplicationSettings
from limen.knowledge.contracts import EmbeddingProvider

_cache_lock = threading.Lock()
_cached_provider: EmbeddingProvider | None = None
_cached_key: str | None = None

# Canonical HF id for the challenge baseline (CPU-friendly, 384-d).
CANONICAL_E5_MODEL_ID = "intfloat/multilingual-e5-small"
EXPECTED_E5_DIMENSIONS = 384

_WEIGHT_CANDIDATES = (
    "model.safetensors",
    "pytorch_model.bin",
    "model.safetensors.index.json",
)


def local_model_dir_usable(path: Path) -> bool:
    """True when ``path`` looks like a loadable sentence-transformers / HF checkout."""
    if not path.is_dir():
        return False
    config = path / "config.json"
    if not config.is_file() and not (path / "modules.json").is_file():
        # Prefer config.json; modules.json covers some sentence-transformers layouts.
        return False
    for name in _WEIGHT_CANDIDATES:
        candidate = path / name
        if candidate.is_file() and candidate.stat().st_size > 1_000:
            return True
        # sharded safetensors
        if name.endswith(".index.json") and candidate.is_file():
            return True
    # Some checkouts only ship onnx / rust; require at least config + tokenizer.
    return (path / "tokenizer.json").is_file() or (path / "tokenizer_config.json").is_file()


class StubEmbeddingProvider:
    """Deterministic bag-of-words embedding for tests and cold-start."""

    def __init__(self, dimensions: int = 64) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_id(self) -> str:
        return f"stub-d{self._dimensions}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in text.lower().split():
            idx = hash(token) % self._dimensions
            vector[idx] += 1.0
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]


def uses_e5_prefixes(model_name: str) -> bool:
    """E5 models expect asymmetric query/passage prefixes (HuggingFace card)."""
    name = model_name.lower().replace("\\", "/")
    base = name.rsplit("/", 1)[-1]
    return "e5-" in name or "e5-" in base or base.startswith("e5") or name.endswith("/e5")


def _is_local_dir(model_name: str) -> bool:
    path = Path(model_name)
    return path.is_dir()


def format_e5_query(text: str) -> str:
    return f"query: {text}"


def format_e5_passage(text: str) -> str:
    return f"passage: {text}"


class SentenceTransformersEmbeddingProvider:
    """Local multilingual embeddings via sentence-transformers (lazy load).

    Model-specific formatting (E5 query:/passage: prefixes) stays inside this
    adapter — domain/orchestrator code never sees it.
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._use_e5_prefixes = uses_e5_prefixes(model_name)
        self._model = None
        self._dimensions: int | None = None

    @property
    def dimensions(self) -> int:
        self._ensure_model()
        assert self._dimensions is not None
        return self._dimensions

    @property
    def model_id(self) -> str:
        return self.model_name

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self._ensure_model()
        model = self._model
        assert model is not None
        prepared = [format_e5_passage(text) if self._use_e5_prefixes else text for text in texts]
        vectors = model.encode(prepared, normalize_embeddings=True)
        return [list(map(float, row)) for row in vectors]

    def embed_query(self, text: str) -> list[float]:
        self._ensure_model()
        model = self._model
        assert model is not None
        prepared = format_e5_query(text) if self._use_e5_prefixes else text
        vector = model.encode([prepared], normalize_embeddings=True)[0]
        return list(map(float, vector))

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "sentence-transformers is required for EMBEDDING_PROVIDER="
                "sentence-transformers. Install with: "
                "`python scripts/install_embeddings_cpu.py` "
                "(CPU-first; no CUDA required)."
            ) from error
        try:
            model = SentenceTransformer(
                self.model_name,
                local_files_only=_is_local_dir(self.model_name),
            )
        except Exception as error:
            raise RuntimeError(
                "Failed to resolve embedding model "
                f"{self.model_name!r}. Set EMBEDDING_MODEL_PATH to a local "
                f"checkout, or ensure Hugging Face can download "
                f"{CANONICAL_E5_MODEL_ID}. Original error: {error}"
            ) from error
        probe_text = (
            format_e5_passage("dimension probe") if self._use_e5_prefixes else "dimension probe"
        )
        probe = model.encode([probe_text], normalize_embeddings=True)
        self._model = model
        self._dimensions = int(len(probe[0]))


def resolve_embedding_model_name(settings: ApplicationSettings) -> str:
    """Deterministic model resolution for challenge evaluators.

    A. ``EMBEDDING_MODEL_PATH`` if set and usable.
    B. ``EMBEDDING_MODEL`` when it points at a usable local directory,
       otherwise the Hugging Face model id (default:
       ``intfloat/multilingual-e5-small``).
    C. Callers that need the weights must load via sentence-transformers;
       failure surfaces a clear RuntimeError (no private mirrors).
    """
    path_cfg = (settings.embedding_model_path or "").strip()
    if path_cfg:
        path = Path(path_cfg).expanduser()
        if local_model_dir_usable(path):
            return str(path.resolve())
        raise RuntimeError(
            f"EMBEDDING_MODEL_PATH={path_cfg!r} is set but is not a usable "
            "local model directory (expected config + weights)."
        )

    configured = (settings.embedding_model or "").strip()
    if not configured or configured == "stub-embedding":
        return CANONICAL_E5_MODEL_ID

    as_path = Path(configured).expanduser()
    if as_path.is_dir():
        if local_model_dir_usable(as_path):
            return str(as_path.resolve())
        raise RuntimeError(
            f"EMBEDDING_MODEL={configured!r} looks like a directory but is "
            "not a usable local model checkout."
        )
    return configured


def local_model_available(settings: ApplicationSettings) -> bool:
    """True when a local checkout is configured/usable (no Hub download needed)."""
    path_cfg = (settings.embedding_model_path or "").strip()
    if path_cfg:
        return local_model_dir_usable(Path(path_cfg).expanduser())
    configured = (settings.embedding_model or "").strip()
    if configured:
        as_path = Path(configured).expanduser()
        if as_path.is_dir():
            return local_model_dir_usable(as_path)
    return False


def _embedding_cache_key(settings: ApplicationSettings) -> str:
    provider = settings.embedding_provider.lower().strip()
    if provider == "stub":
        return f"stub|{settings.embedding_dimensions}"
    return f"{provider}|{resolve_embedding_model_name(settings)}"


def reset_embedding_provider_for_tests() -> None:
    """Drop process-wide embedding singleton (tests only)."""
    global _cached_provider, _cached_key
    with _cache_lock:
        _cached_provider = None
        _cached_key = None


def build_embedding_provider(settings: ApplicationSettings) -> EmbeddingProvider:
    """Return a process-wide singleton per embedding configuration.

    Loading multilingual-e5 twice OOMs challenge laptops; every request must
    reuse the same SentenceTransformer weights.
    """
    global _cached_provider, _cached_key
    key = _embedding_cache_key(settings)
    with _cache_lock:
        if _cached_provider is not None and _cached_key == key:
            return _cached_provider

        provider = settings.embedding_provider.lower().strip()
        if provider == "stub":
            built: EmbeddingProvider = StubEmbeddingProvider(
                dimensions=settings.embedding_dimensions
            )
        elif provider in {"sentence-transformers", "st", "local"}:
            model = resolve_embedding_model_name(settings)
            built = SentenceTransformersEmbeddingProvider(model_name=model)
        else:
            raise ValueError(
                f"Unsupported EMBEDDING_PROVIDER={settings.embedding_provider!r}. "
                "Use 'stub' or 'sentence-transformers'."
            )
        _cached_provider = built
        _cached_key = key
        return built


def embedding_fingerprint(settings: ApplicationSettings, *, dimensions: int) -> str:
    """Identity for vector collections — prevents mixing incompatible models."""
    provider = settings.embedding_provider.lower().strip()
    if provider == "stub":
        model = f"stub-d{dimensions}"
    else:
        raw = resolve_embedding_model_name(settings)
        # Normalize local paths to a stable logical model id for fingerprints.
        model = (
            CANONICAL_E5_MODEL_ID
            if raw.replace("\\", "/").rstrip("/").endswith("multilingual-e5-small")
            else raw
        )
    return f"{provider}|{model}|d{dimensions}|cosine"


def default_dense_min_score(settings: ApplicationSettings) -> float:
    """Provider-aware baseline; explicit DENSE_MIN_SCORE always wins."""
    if settings.dense_min_score is not None:
        return float(settings.dense_min_score)
    provider = settings.embedding_provider.lower().strip()
    if provider == "stub":
        return 0.35
    # Calibrated 2026-08-08 on intfloat/multilingual-e5-small (local checkout):
    # relevant bilingual tops ≈0.80–0.84; off-domain food/transit vs diet doc ≈0.79;
    # midpoint-oriented floor 0.795 (see evals/calibrate_dense_scores.py).
    return 0.795
