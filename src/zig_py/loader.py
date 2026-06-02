"""ctypes loader for Zig shared libraries built by zig-PY."""

from __future__ import annotations

import ctypes
from pathlib import Path

from . import logging as log
from .build import BUILD_ROOT, shared_library_name

SHARED_LIBRARY_LOAD_FAILURE = 30


def default_add_library_path() -> Path:
    return BUILD_ROOT / "add" / shared_library_name("add")


def load_add_library(path: str | Path | None = None) -> ctypes.CDLL:
    library_path = Path(path) if path is not None else default_add_library_path()
    log.info(f"loading Zig shared library from {library_path}")
    if not library_path.exists():
        log.error(f"shared library does not exist: {library_path}")
        log.fix("Run make build-example before loading the add example.")
        raise SystemExit(SHARED_LIBRARY_LOAD_FAILURE)
    try:
        library = ctypes.CDLL(str(library_path))
    except OSError as exc:
        log.error(f"failed to load shared library {library_path}: {exc}")
        log.fix("Rebuild with make build-example and confirm the library matches this platform.")
        raise SystemExit(SHARED_LIBRARY_LOAD_FAILURE) from exc
    library.add.argtypes = [ctypes.c_int32, ctypes.c_int32]
    library.add.restype = ctypes.c_int32
    log.ok(f"loaded add(a: i32, b: i32) from {library_path}")
    return library
