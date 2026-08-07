import asyncio

from limen.config.settings import ApplicationSettings
from limen.intelligence.contracts import LLMRequest
from limen.intelligence.providers.factory import build_llm_provider
from limen.knowledge.embeddings import build_embedding_provider
from limen.voice.stt import build_stt_provider
from limen.voice.tts import build_tts_provider


def test_stub_providers_satisfy_contracts() -> None:
    settings = ApplicationSettings(
        LLM_PROVIDER="stub",
        STT_PROVIDER="stub",
        TTS_PROVIDER="stub",
        EMBEDDING_PROVIDER="stub",
        _env_file=None,
    )
    llm = build_llm_provider(settings)
    stt = build_stt_provider(settings)
    tts = build_tts_provider(settings)
    emb = build_embedding_provider(settings)

    async def _run() -> None:
        text = await llm.generate_text(LLMRequest(prompt="hola"))
        assert text.text
        transcript = await stt.transcribe(b"fake")
        assert transcript.text
        audio = await tts.synthesize("hola", "default")
        assert audio.audio
        vectors = emb.embed_documents(["a", "b"])
        assert len(vectors) == 2
        assert len(emb.embed_query("a")) == len(vectors[0])

    asyncio.run(_run())
