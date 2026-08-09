#!/usr/bin/env python3
"""Install CPU-first PyTorch + sentence-transformers into the active environment.

Challenge baseline does not require CUDA. This script:

1. Installs ``torch`` from the official PyTorch CPU wheel index.
2. Installs ``sentence-transformers``.

GPU/CUDA wheels remain optional and are never selected by this path.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

TORCH_CPU_INDEX = "https://download.pytorch.org/whl/cpu"


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-torch",
        action="store_true",
        help="Only install sentence-transformers (assumes torch already present)",
    )
    args = parser.parse_args()

    pip_base = [sys.executable, "-m", "pip"]

    if not args.skip_torch:
        _run(
            [
                *pip_base,
                "install",
                "--upgrade",
                "torch",
                "--index-url",
                TORCH_CPU_INDEX,
            ]
        )

    _run([*pip_base, "install", "--upgrade", "sentence-transformers>=3.0.0"])
    print("CPU-first embedding dependencies installed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
