"""Resolve CUDA 12 user-space libraries shipped via pip (nvidia-*-cu12).

Must run before CTranslate2 / faster-whisper import so dlopen finds
libcublas.so.12 without touching system CUDA 13 or inventing SONAME symlinks.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path


def _site_packages() -> list[Path]:
    roots: list[Path] = []
    for entry in sys.path:
        if not entry:
            continue
        path = Path(entry)
        if path.name == "site-packages" and path.is_dir():
            roots.append(path)
        # editable / venv layout
        candidate = path / "site-packages"
        if candidate.is_dir():
            roots.append(candidate)
    # Deduplicate
    seen: set[str] = set()
    ordered: list[Path] = []
    for root in roots:
        key = str(root.resolve())
        if key in seen:
            continue
        seen.add(key)
        ordered.append(root)
    return ordered


def discover_cuda12_lib_dirs() -> list[Path]:
    """Return directories that contain nvidia cu12 shared libraries."""
    dirs: list[Path] = []
    for site in _site_packages():
        for pkg in ("nvidia/cublas/lib", "nvidia/cudnn/lib", "nvidia/cuda_runtime/lib"):
            candidate = site / pkg
            if candidate.is_dir():
                dirs.append(candidate)
    # Also honor an explicit override for operators.
    override = os.environ.get("LIMEN_CUDA12_LIB_DIR", "").strip()
    if override:
        path = Path(override)
        if path.is_dir():
            dirs.insert(0, path)
    seen: set[str] = set()
    out: list[Path] = []
    for directory in dirs:
        key = str(directory.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(directory)
    return out


def cuda12_libs_ready() -> dict[str, object]:
    """Inspect whether libcublas.so.12 is resolvable from pip packages."""
    dirs = discover_cuda12_lib_dirs()
    cublas = None
    cudnn = None
    for directory in dirs:
        for name in ("libcublas.so.12", "libcublas.so"):
            hit = directory / name
            if hit.is_file():
                cublas = hit
                break
        for name in ("libcudnn.so.9", "libcudnn.so"):
            hit = directory / name
            if hit.is_file():
                cudnn = hit
                break
    return {
        "lib_dirs": [str(d) for d in dirs],
        "libcublas": str(cublas) if cublas else None,
        "libcudnn": str(cudnn) if cudnn else None,
        "ready": cublas is not None,
    }


@lru_cache(maxsize=1)
def ensure_cuda12_library_path() -> dict[str, object]:
    """Prepend pip CUDA 12 lib dirs to LD_LIBRARY_PATH for this process.

    Safe to call multiple times. Does not modify global /usr libraries.
    """
    info = cuda12_libs_ready()
    raw_dirs = info.get("lib_dirs")
    dirs = [Path(str(p)) for p in raw_dirs] if isinstance(raw_dirs, list) else []
    if not dirs:
        return {**info, "applied": False, "reason": "no_cuda12_pip_libs"}

    existing = os.environ.get("LD_LIBRARY_PATH", "")
    parts = [str(d) for d in dirs]
    for piece in existing.split(":"):
        if piece and piece not in parts:
            parts.append(piece)
    new_path = ":".join(parts)
    os.environ["LD_LIBRARY_PATH"] = new_path

    # Also try loading via ctypes so subsequent dlopen from CT2 can succeed
    # even when the dynamic linker cached the old path (best-effort).
    try:
        import ctypes

        for directory in dirs:
            for lib in sorted(directory.glob("lib*.so*")):
                if ".so" not in lib.name:
                    continue
                # Prefer versioned CUDA 12 / cuDNN 9 sonames.
                if not any(
                    tag in lib.name for tag in ("cublas", "cudnn", "cudart", "nvrtc", "nvJitLink")
                ):
                    continue
                try:
                    ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    continue
    except Exception as exc:  # noqa: BLE001
        return {
            **info,
            "applied": True,
            "ld_library_path": new_path,
            "ctypes_note": f"{type(exc).__name__}:{exc}",
        }

    return {
        **info,
        "applied": True,
        "ld_library_path": new_path,
    }
