#!/usr/bin/env python3
"""Generate deterministic Spanish WAV fixtures via Piper (no private recordings)."""

from __future__ import annotations

import argparse
import math
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from limen.voice.audio_codec import write_pcm16_wav
from limen.voice.providers.piper_tts import PiperTTSProvider

FIXTURES = ROOT / "tests" / "fixtures" / "voice"

# Eval-only phrases (NOT hard-coded into clinical logic).
UTTERANCES: dict[str, str] = {
    "es_clean_air.wav": "Me falta el aire y me duele el pecho.",
    "es_red_breath.wav": "No puedo respirar desde esta mañana.",
    "es_green_ok.wav": "Todo bien, solo quería confirmar la cita de control.",
    "es_col_aire.wav": "Me falta el aire.",
    "es_col_aguita.wav": "Me está saliendo como agüita.",
    "es_col_arde.wav": "Me arde resto.",
    "es_col_abrio.wav": "Se me abrió un poquito.",
    "es_col_vuelto.wav": "Me siento vuelto nada.",
    "es_negation.wav": "No me duele el pecho y no tengo fiebre.",
    "es_numbers.wav": "Tengo treinta y ocho punto cinco de temperatura desde hace dos días.",
    "es_meds.wav": "Tomé el acetaminofén hace cuatro horas.",
}


def _mix_noise(pcm: bytes, *, amplitude: float = 0.08) -> bytes:
    out = bytearray()
    for i in range(0, len(pcm), 2):
        sample = struct.unpack_from("<h", pcm, i)[0]
        noise = int(amplitude * 32767 * math.sin(i * 0.017) * math.sin(i * 0.003))
        mixed = max(-32768, min(32767, sample + noise))
        out.extend(struct.pack("<h", mixed))
    return bytes(out)


def _scale_volume(pcm: bytes, *, gain: float) -> bytes:
    out = bytearray()
    for i in range(0, len(pcm), 2):
        sample = int(struct.unpack_from("<h", pcm, i)[0] * gain)
        sample = max(-32768, min(32767, sample))
        out.extend(struct.pack("<h", sample))
    return bytes(out)


def _insert_pauses(pcm: bytes, sample_rate: int) -> bytes:
    # Split into thirds and insert 400ms silence between.
    silence = b"\x00\x00" * int(sample_rate * 0.4)
    n = len(pcm) // 2
    a = (n // 3) * 2
    b = (2 * n // 3) * 2
    return pcm[:a] + silence + pcm[a:b] + silence + pcm[b:]


def _wav_pcm(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        rate = wf.getframerate()
        return wf.readframes(wf.getnframes()), rate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--voice-dir",
        default=str(ROOT / "runtime" / "models" / "piper"),
        help="Directory containing es_MX-claude-high.onnx",
    )
    args = parser.parse_args()
    FIXTURES.mkdir(parents=True, exist_ok=True)

    tts = PiperTTSProvider(
        voice="es_MX-claude-high",
        download_dir=args.voice_dir,
    )
    # Sync generate via private API for offline fixture build.
    for name, text in UTTERANCES.items():
        result = tts._synthesize_sync(text, "es_MX-claude-high")  # noqa: SLF001
        dest = FIXTURES / name
        dest.write_bytes(result.audio)
        print(f"OK {dest.name} duration_ms={result.duration_ms:.0f}")

    # Controlled noise variants from clean_air.
    clean = FIXTURES / "es_clean_air.wav"
    pcm, rate = _wav_pcm(clean)
    (FIXTURES / "es_noise_bg.wav").write_bytes(
        write_pcm16_wav(_mix_noise(pcm), sample_rate_hz=rate, channels=1)
    )
    (FIXTURES / "es_low_volume.wav").write_bytes(
        write_pcm16_wav(_scale_volume(pcm, gain=0.25), sample_rate_hz=rate, channels=1)
    )
    (FIXTURES / "es_pause_heavy.wav").write_bytes(
        write_pcm16_wav(_insert_pauses(pcm, rate), sample_rate_hz=rate, channels=1)
    )
    print(f"OK noise variants under {FIXTURES}")
    print("FIXTURES_READY=TRUE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
