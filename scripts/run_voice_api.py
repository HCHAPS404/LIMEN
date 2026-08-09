"""Launch LIMEN API with CUDA 12 pip libraries on LD_LIBRARY_PATH.

Use for challenge voice so CTranslate2 finds libcublas.so.12 before import.
Does not downgrade the system NVIDIA driver / CUDA 13 toolkit.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from limen.voice.cuda_runtime import ensure_cuda12_library_path


def main(argv: list[str] | None = None) -> int:
    info = ensure_cuda12_library_path()
    if not info.get("ready"):
        print(
            "WARN: CUDA 12 pip libs not ready; STT_DEVICE=cuda may fail. "
            "Install: .venv/bin/pip install 'nvidia-cublas-cu12' 'nvidia-cudnn-cu12==9.*'",
            file=sys.stderr,
        )
    else:
        print(
            f"CUDA12 libs ready: cublas={info.get('libcublas')} "
            f"dirs={len(info.get('lib_dirs') or [])}",
            file=sys.stderr,
        )

    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        args = [
            "uvicorn",
            "apps.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
    # Re-exec so child inherits LD_LIBRARY_PATH from process start.
    os.execvpe(args[0], args, os.environ)
    return 1


if __name__ == "__main__":
    # Prefer invoking via the venv python module path that is already on PATH
    # when called as: .venv/bin/python scripts/run_voice_api.py
    # For uvicorn, use absolute python -m when first arg is bare "uvicorn".
    argv = sys.argv[1:]
    if not argv:
        py = sys.executable
        argv = [
            py,
            "-m",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
    elif argv[0] == "uvicorn":
        argv = [sys.executable, "-m", *argv]
    raise SystemExit(main(argv))
