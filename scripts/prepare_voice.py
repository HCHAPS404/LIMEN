#!/usr/bin/env python3
"""Prepare challenge voice assets (Piper voice + Whisper model cache check).

Does not commit model weights. Idempotent: skips downloads that already exist.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PIPER_VOICE = "es_MX-claude-high"
PIPER_DIR = ROOT / "runtime" / "models" / "piper"
# Official rhasspy/piper-voices (MIT) — Mexican Spanish female, high quality.
PIPER_FILES = {
    f"{PIPER_VOICE}.onnx": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
        f"es/es_MX/claude/high/{PIPER_VOICE}.onnx"
    ),
    f"{PIPER_VOICE}.onnx.json": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
        f"es/es_MX/claude/high/{PIPER_VOICE}.onnx.json"
    ),
}
WHISPER_ID = "Systran/faster-whisper-small"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    print(f"Downloading {url} → {dest}")
    urllib.request.urlretrieve(url, tmp)  # noqa: S310 — fixed HTTPS model URLs
    tmp.replace(dest)


def prepare_piper(*, force: bool = False) -> Path:
    PIPER_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in PIPER_FILES.items():
        path = PIPER_DIR / name
        if path.is_file() and path.stat().st_size > 0 and not force:
            print(f"OK exists: {path} ({path.stat().st_size} bytes)")
            continue
        _download(url, path)
        print(f"OK downloaded: {path} ({path.stat().st_size} bytes)")
    onnx = PIPER_DIR / f"{PIPER_VOICE}.onnx"
    cfg = PIPER_DIR / f"{PIPER_VOICE}.onnx.json"
    if not onnx.is_file() or not cfg.is_file():
        raise SystemExit("Piper voice assets incomplete")
    return onnx


def prepare_whisper(*, download: bool = True) -> dict[str, object]:
    """Verify faster-whisper import; optionally trigger model download via load."""
    from limen.voice.cuda_runtime import ensure_cuda12_library_path

    info: dict[str, object] = {"model_id": WHISPER_ID, "loaded": False}
    info["cuda12"] = ensure_cuda12_library_path()
    try:
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]
    except ImportError as exc:
        raise SystemExit(
            "faster-whisper not installed. Run: .venv/bin/pip install -e '.[voice]'"
        ) from exc

    device = "cpu"
    compute = "int8"
    try:
        import ctranslate2

        if int(ctranslate2.get_cuda_device_count()) > 0:
            device = "cuda"
            compute = "float16"
            try:
                import subprocess

                proc = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    info["cuda_device_name"] = proc.stdout.strip().splitlines()[0]
            except Exception:  # noqa: BLE001
                pass
    except Exception as exc:  # noqa: BLE001
        info["cuda_probe"] = f"{type(exc).__name__}:{exc}"

    info["device_preferred"] = device
    info["compute_type_preferred"] = compute
    if not download:
        print(f"Whisper import OK; skip load (preferred_device={device})")
        return info

    print(f"Loading Whisper model {WHISPER_ID} preferred={device}/{compute} …")
    last_error: Exception | None = None
    for try_device, try_compute in [(device, compute)] + (
        [("cuda", "int8_float16")] if device == "cuda" else []
    ) + ([("cpu", "int8")] if device == "cuda" else []):
        try:
            model = WhisperModel(WHISPER_ID, device=try_device, compute_type=try_compute)
            import numpy as np  # type: ignore[import-untyped]

            _segments, _info = model.transcribe(
                np.zeros(16000, dtype=np.float32),
                language="es",
                beam_size=1,
                vad_filter=False,
            )
            list(_segments)
            info["device"] = try_device
            info["compute_type"] = try_compute
            info["loaded"] = True
            if try_device != device:
                info["fallback"] = f"from_{device}_to_{try_device}"
            print(f"OK Whisper model ready on {try_device}/{try_compute}")
            return info
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"WARN load failed {try_device}/{try_compute}: {exc}")
    raise SystemExit(f"Whisper load failed: {last_error}")


def write_license_note(path: Path) -> None:
    path.write_text(
        "Piper voice es_MX-claude-high from rhasspy/piper-voices (MIT).\n"
        "Source: https://huggingface.co/rhasspy/piper-voices\n"
        "Do not commit *.onnx weights to git.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Redownload Piper assets")
    parser.add_argument(
        "--skip-whisper-load",
        action="store_true",
        help="Only verify faster-whisper import (no model download)",
    )
    args = parser.parse_args()

    onnx = prepare_piper(force=args.force)
    write_license_note(PIPER_DIR / "LICENSE_NOTE.txt")
    whisper = prepare_whisper(download=not args.skip_whisper_load)
    digest = hashlib.sha256(onnx.read_bytes()).hexdigest()[:16]
    print("---")
    print(f"PIPER_VOICE={PIPER_VOICE}")
    print(f"PIPER_ONNX={onnx}")
    print(f"PIPER_ONNX_SHA256_16={digest}")
    print(f"WHISPER_MODEL={whisper['model_id']}")
    print(f"WHISPER_DEVICE={whisper.get('device')}")
    print(f"WHISPER_LOADED={whisper.get('loaded')}")
    print("READY_FOR_REAL_VOICE_ASSETS=TRUE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
