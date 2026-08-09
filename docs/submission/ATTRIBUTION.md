# Third-party attribution (runtime tools & models)

LIMEN itself is MIT-licensed (`LICENSE`). Runtime models and libraries are
**not redistributed in this repository**; operators download them via documented
`make prepare-*` targets / package installs.

| Component | Role in LIMEN | Notes |
| --- | --- | --- |
| Microsoft Phi-3.5 (via Ollama tag `phi3.5`) | Patient-facing LLM | Subject to model/provider terms; not safety authority |
| intfloat/multilingual-e5-small | Dense embeddings | Hugging Face model card / license |
| Systran/faster-whisper-small | STT | Faster-Whisper / model card terms |
| Piper `es_MX-claude-high` (rhasspy/piper-voices) | TTS | Piper voice license on upstream |
| Qdrant (local embedded client) | Vector store | Qdrant licensing for the client you install |
| PyTorch / sentence-transformers | Embedding runtime | Respective OSS licenses |
| Ollama | Local LLM runner | Ollama terms |
| React / Vite / FastAPI / SQLite | App stack | OSS licenses via package metadata |

Do not commit model weight blobs. See `.gitignore` and `docs/CHALLENGE_RUNTIME.md`.
