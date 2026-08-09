#!/usr/bin/env python3
"""Calibrate dense_min_score for the real E5 embedding model.

Measures cosine similarities for relevant / weak / unrelated pairs and prints
a conservative threshold recommendation. Does not invent challenge scores.
"""

from __future__ import annotations

import json
import time
from statistics import mean

from limen.config.settings import ApplicationSettings
from limen.knowledge.embeddings import (
    build_embedding_provider,
    default_dense_min_score,
    resolve_embedding_model_name,
)

PAIRS = {
    "relevant": [
        (
            "me está saliendo como agüita de la herida",
            "Serous wound drainage may appear as clear or pale fluid seeping from the incision.",
        ),
        (
            "me falta el aire",
            "Shortness of breath (dyspnea) after surgery requires prompt clinical review.",
        ),
        (
            "se me abrió un poquito la herida",
            "Partial wound dehiscence means the surgical incision has opened slightly.",
        ),
        (
            "la herida está roja y caliente",
            "Peri-incisional erythema with warmth can indicate local inflammation.",
        ),
    ],
    "weak": [
        (
            "tengo un poco de cansancio",
            "Shortness of breath (dyspnea) after surgery requires prompt clinical review.",
        ),
        (
            "la cicatriz se ve distinta",
            "Partial wound dehiscence means the surgical incision has opened slightly.",
        ),
    ],
    "unrelated": [
        (
            "horario del metro de Medellín y receta de arepas con hogao",
            "Serous wound drainage may appear as clear or pale fluid seeping from the incision.",
        ),
        (
            "resultados del partido de fútbol anoche",
            "Shortness of breath (dyspnea) after surgery requires prompt clinical review.",
        ),
        (
            "cómo configurar WiFi en el router",
            "Partial wound dehiscence means the surgical incision has opened slightly.",
        ),
    ],
}


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def main() -> int:
    import os

    path = os.environ.get("EMBEDDING_MODEL_PATH", "").strip()
    kwargs: dict = {
        "EMBEDDING_PROVIDER": "sentence-transformers",
        "EMBEDDING_MODEL": "intfloat/multilingual-e5-small",
        "_env_file": None,
    }
    if path:
        kwargs["EMBEDDING_MODEL_PATH"] = path
    settings = ApplicationSettings(**kwargs)
    t0 = time.perf_counter()
    emb = build_embedding_provider(settings)
    dims = emb.dimensions
    init_ms = (time.perf_counter() - t0) * 1000.0

    distributions: dict[str, list[float]] = {}
    for label, pairs in PAIRS.items():
        scores: list[float] = []
        for query, passage in pairs:
            q = emb.embed_query(query)
            p = emb.embed_documents([passage])[0]
            scores.append(_cosine(q, p))
        distributions[label] = scores

    relevant_min = min(distributions["relevant"])
    unrelated_max = max(distributions["unrelated"])
    if relevant_min > unrelated_max:
        # Mid-gap between strongest unrelated and weakest relevant.
        recommended = round((relevant_min + unrelated_max) / 2.0, 3)
    else:
        # Overlapping bands — sit slightly above unrelated_max.
        recommended = round(unrelated_max + 0.02, 3)

    coded_default = default_dense_min_score(
        ApplicationSettings(
            EMBEDDING_PROVIDER="sentence-transformers",
            EMBEDDING_MODEL="intfloat/multilingual-e5-small",
            DENSE_MIN_SCORE=None,
            _env_file=None,
        )
    )

    report = {
        "model": resolve_embedding_model_name(settings),
        "dimensions": dims,
        "normalization": "normalize_embeddings=True (cosine-compatible)",
        "query_formatting": "query: <text>",
        "passage_formatting": "passage: <text>",
        "cold_init_ms": init_ms,
        "score_distributions": {
            label: {
                "scores": [round(s, 4) for s in scores],
                "mean": round(mean(scores), 4),
                "min": round(min(scores), 4),
                "max": round(max(scores), 4),
            }
            for label, scores in distributions.items()
        },
        "relevant_min": round(relevant_min, 4),
        "unrelated_max": round(unrelated_max, 4),
        "recommended_dense_min_score": recommended,
        "coded_default_dense_min_score": coded_default,
        "notes": (
            "Synthetic pairs only. Update limen/knowledge/embeddings.py "
            "default_dense_min_score for E5 if recommendation drifts materially."
        ),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("calibrate_dense_scores: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
