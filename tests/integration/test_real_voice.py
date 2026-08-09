"""Opt-in real voice tests (LIMEN_REAL_VOICE=1). Uses Piper-generated fixtures (no mic)."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from limen.auth.models import StoredAccount
from limen.config.settings import ApplicationSettings
from limen.conversation.call_service import CallService
from limen.intelligence.providers.factory import build_llm_provider
from limen.intelligence.providers.stub import StubLLMProvider
from limen.persistence.database import Database
from limen.persistence.repositories.accounts import SqliteAccountRepository
from limen.persistence.repositories.calls import SqliteCallRepository
from limen.persistence.repositories.traces import SqliteTraceRepository
from limen.safety.decision import Severity
from limen.safety.governor import SafetyGovernor
from limen.voice.audio_codec import silence_wav, wav_duration_ms
from limen.voice.stt import StubSTTProvider, build_stt_provider
from limen.voice.tts import StubTTSProvider, build_tts_provider

pytestmark = pytest.mark.real_voice

_REAL = os.environ.get("LIMEN_REAL_VOICE", "").strip() in {"1", "true", "yes"}
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "voice"
ROOT = Path(__file__).resolve().parents[2]


def _require_real() -> None:
    if not _REAL:
        pytest.skip("Set LIMEN_REAL_VOICE=1 for real voice providers")


def _settings(**overrides: str) -> ApplicationSettings:
    base = {
        "STT_PROVIDER": os.environ.get("STT_PROVIDER", "faster_whisper"),
        "STT_MODEL": os.environ.get("STT_MODEL", "Systran/faster-whisper-small"),
        "STT_DEVICE": os.environ.get("STT_DEVICE", "auto"),
        "TTS_PROVIDER": os.environ.get("TTS_PROVIDER", "piper"),
        "TTS_VOICE": os.environ.get("TTS_VOICE", "es_MX-claude-high"),
        "TTS_MODEL_PATH": os.environ.get(
            "TTS_MODEL_PATH", str(ROOT / "runtime" / "models" / "piper")
        ),
        "LLM_PROVIDER": os.environ.get("LLM_PROVIDER", "ollama"),
        "LLM_MODEL": os.environ.get("LLM_MODEL", "phi3.5"),
        "EMBEDDING_PROVIDER": "stub",
    }
    base.update(overrides)
    return ApplicationSettings(**base, _env_file=None)


def _service(tmp_path: Path, *, llm=None) -> tuple[CallService, str]:
    db = Database(tmp_path / "real_voice.sqlite3")
    db.initialize()
    accounts = SqliteAccountRepository(db)
    account = StoredAccount(
        account_id=str(uuid.uuid4()),
        email=f"rv-{uuid.uuid4().hex[:8]}@limen.local",
        display_name="Real Voice",
        created_at=datetime.now(tz=UTC),
        password_hash="x",
    )
    accounts.insert_account(account)
    return (
        CallService(
            SqliteCallRepository(db),
            SqliteTraceRepository(db),
            llm=llm or StubLLMProvider(),
            governor=SafetyGovernor(),
        ),
        account.account_id,
    )


@pytest.mark.asyncio
async def test_real_faster_whisper_and_piper_when_configured() -> None:
    _require_real()
    settings = _settings()
    try:
        stt = build_stt_provider(settings)
        tts = build_tts_provider(settings)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"voice providers unavailable: {exc}")

    stt_health = await stt.health()  # type: ignore[misc]
    if not stt_health.get("ok"):
        pytest.skip(f"STT not ready: {stt_health}")
    tts_health = await tts.health()  # type: ignore[misc]
    if not tts_health.get("ok"):
        pytest.skip(f"TTS not ready: {tts_health}")

    transcript = await stt.transcribe(silence_wav(duration_ms=500), language="es")
    assert transcript.provider == "faster_whisper"
    # Silence must not invent clinical content.
    assert "respir" not in (transcript.text or "").casefold()

    audio = await tts.synthesize(
        "Gracias. Observe cómo se siente y avise si empeora.",
        settings.tts_voice,
    )
    assert audio.audio[:4] == b"RIFF"
    assert audio.provider == "piper"
    assert (wav_duration_ms(audio.audio) or 0) > 0
    assert audio.latency_ms is not None


@pytest.mark.asyncio
async def test_real_stt_spanish_fixture() -> None:
    _require_real()
    path = FIXTURES / "es_clean_air.wav"
    if not path.is_file():
        pytest.skip("Run make prepare-voice (fixtures)")
    settings = _settings()
    stt = build_stt_provider(settings)
    health = await stt.health()  # type: ignore[misc]
    if not health.get("ok"):
        pytest.skip(f"STT not ready: {health}")

    transcript = await stt.transcribe(path.read_bytes(), language="es")
    text = (transcript.normalized_text or transcript.text or "").casefold()
    assert "aire" in text or "falta" in text
    assert transcript.latency_ms is not None and transcript.latency_ms > 0
    assert health.get("device") in {"cpu", "cuda"}
    if os.environ.get("STT_DEVICE", "").strip().lower() == "cuda":
        assert health.get("actual_device") == "cuda", health
        assert health.get("ok") is True


@pytest.mark.asyncio
async def test_real_tts_spanish_wav() -> None:
    _require_real()
    settings = _settings()
    tts = build_tts_provider(settings)
    health = await tts.health()  # type: ignore[misc]
    if not health.get("ok"):
        pytest.skip(f"TTS not ready: {health}")
    audio = await tts.synthesize(
        "Busque atención médica de urgencia ahora.",
        settings.tts_voice,
    )
    assert audio.audio[:4] == b"RIFF"
    duration = wav_duration_ms(audio.audio) or 0.0
    assert duration > 200
    assert len(audio.audio) > 1000


@pytest.mark.asyncio
async def test_real_pipeline_wav_to_tts(tmp_path: Path) -> None:
    _require_real()
    path = FIXTURES / "es_green_ok.wav"
    if not path.is_file():
        pytest.skip("missing fixture")
    settings = _settings()
    stt = build_stt_provider(settings)
    tts = build_tts_provider(settings)
    if not (await stt.health()).get("ok") or not (await tts.health()).get("ok"):  # type: ignore[misc]
        pytest.skip("providers not ready")

    llm = build_llm_provider(settings)
    service, account_id = _service(tmp_path, llm=llm)
    created = service.create(account_id=account_id, patient_alias="pipeline")
    transcript = await stt.transcribe(path.read_bytes(), language="es")
    assert transcript.text.strip()
    result = await service.process_text_turn(
        account_id=account_id,
        call_id=created["call_id"],
        user_text=transcript.normalized_text or transcript.text,
    )
    assert result is not None
    assert result.assistant_text.strip()
    speech = await tts.synthesize(result.assistant_text, settings.tts_voice)
    assert speech.audio[:4] == b"RIFF"
    assert (wav_duration_ms(speech.audio) or 0) > 0


@pytest.mark.asyncio
async def test_real_red_voice_escalates(tmp_path: Path) -> None:
    _require_real()
    path = FIXTURES / "es_red_breath.wav"
    if not path.is_file():
        pytest.skip("missing fixture")
    settings = _settings()
    stt = build_stt_provider(settings)
    tts = build_tts_provider(settings)
    # Stub LLM so generative path cannot invent a downgrade; governor remains source of floor.
    service, account_id = _service(tmp_path, llm=StubLLMProvider())
    created = service.create(account_id=account_id, patient_alias="red")
    transcript = await stt.transcribe(path.read_bytes(), language="es")
    text = transcript.normalized_text or transcript.text
    assert "respir" in text.casefold() or "puedo" in text.casefold()
    result = await service.process_text_turn(
        account_id=account_id,
        call_id=created["call_id"],
        user_text=text,
    )
    assert result is not None
    assert result.safety.severity == Severity.RED
    assert result.safety.escalate is True
    speech = await tts.synthesize(result.assistant_text, settings.tts_voice)
    assert (wav_duration_ms(speech.audio) or 0) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("wav", "tokens"),
    [
        ("es_col_aire.wav", ("falta", "aire")),
        ("es_col_aguita.wav", ("aguita", "agüita", "agua", "abuita")),
        ("es_col_arde.wav", ("arde",)),
        ("es_col_abrio.wav", ("abri",)),
        ("es_col_vuelto.wav", ("vuelto", "nada")),
    ],
)
async def test_real_colombian_phrases(wav: str, tokens: tuple[str, ...]) -> None:
    _require_real()
    path = FIXTURES / wav
    if not path.is_file():
        pytest.skip("missing fixture")
    stt = build_stt_provider(_settings())
    if not (await stt.health()).get("ok"):  # type: ignore[misc]
        pytest.skip("STT not ready")
    transcript = await stt.transcribe(path.read_bytes(), language="es")
    text = (transcript.normalized_text or transcript.text or "").casefold()
    assert any(tok in text for tok in tokens), text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "wav",
    ["es_noise_bg.wav", "es_low_volume.wav", "es_pause_heavy.wav"],
)
async def test_real_controlled_noise_preserves_semantics(wav: str) -> None:
    _require_real()
    path = FIXTURES / wav
    if not path.is_file():
        pytest.skip("missing fixture")
    stt = build_stt_provider(_settings())
    if not (await stt.health()).get("ok"):  # type: ignore[misc]
        pytest.skip("STT not ready")
    transcript = await stt.transcribe(path.read_bytes(), language="es")
    text = (transcript.normalized_text or transcript.text or "").casefold()
    assert "aire" in text or "falta" in text or "pecho" in text


@pytest.mark.asyncio
async def test_real_negation_preserved() -> None:
    _require_real()
    path = FIXTURES / "es_negation.wav"
    if not path.is_file():
        pytest.skip("missing fixture")
    stt = build_stt_provider(_settings())
    transcript = await stt.transcribe(path.read_bytes(), language="es")
    text = (transcript.normalized_text or transcript.text or "").casefold()
    assert "no" in text


@pytest.mark.asyncio
async def test_degraded_stt_unavailable_no_invented_transcript() -> None:
    _require_real()
    # Force broken path: invalid model id should fail observably.
    settings = _settings(STT_MODEL="/nonexistent/whisper-model-path-xyz")
    stt = build_stt_provider(settings)
    health = await stt.health()  # type: ignore[misc]
    assert health.get("ok") is False
    with pytest.raises(RuntimeError):
        await stt.transcribe(silence_wav(duration_ms=200), language="es")


@pytest.mark.asyncio
async def test_degraded_tts_unavailable_text_still_usable(tmp_path: Path) -> None:
    _require_real()
    settings = _settings(TTS_MODEL_PATH="/nonexistent/piper-dir")
    tts = build_tts_provider(settings)
    health = await tts.health()  # type: ignore[misc]
    assert health.get("ok") is False
    service, account_id = _service(tmp_path, llm=StubLLMProvider())
    created = service.create(account_id=account_id, patient_alias="tts-fail")
    result = await service.process_text_turn(
        account_id=account_id,
        call_id=created["call_id"],
        user_text="tengo un poco de molestia",
    )
    assert result is not None
    assert result.assistant_text.strip()
    with pytest.raises(RuntimeError):
        await tts.synthesize(result.assistant_text, "es_MX-claude-high")


@pytest.mark.asyncio
async def test_degraded_ollama_falls_back_deterministic(tmp_path: Path) -> None:
    _require_real()
    settings = _settings(LLM_BASE_URL="http://127.0.0.1:9", LLM_PROVIDER="ollama")
    llm = build_llm_provider(settings)
    service, account_id = _service(tmp_path, llm=llm)
    created = service.create(account_id=account_id, patient_alias="llm-fail")
    result = await service.process_text_turn(
        account_id=account_id,
        call_id=created["call_id"],
        user_text="No puedo respirar desde esta mañana",
    )
    assert result is not None
    assert result.safety.escalate is True
    assert result.assistant_text.strip()


@pytest.mark.asyncio
async def test_temp_audio_cleanup_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _require_real()
    from types import SimpleNamespace

    from apps.api.routers import calls as calls_router

    settings = SimpleNamespace(log_path=str(tmp_path / "logs" / "app.log"))
    audio = silence_wav(duration_ms=100)
    path = calls_router._write_transient_voice_wav(
        settings, call_id="c1", turn_seq=1, audio=audio
    )
    assert path.is_file()
    calls_router._cleanup_transient_voice_wav(path)
    assert not path.exists()


@pytest.mark.asyncio
async def test_stub_providers_still_distinct_from_real() -> None:
    # Always runs even without LIMEN_REAL_VOICE — sanity that stubs remain stubs.
    stt = StubSTTProvider()
    tts = StubTTSProvider()
    t = await stt.transcribe(b"x", language="es")
    assert t.provider == "stub"
    a = await tts.synthesize("hola", "default")
    assert a.provider == "stub"
