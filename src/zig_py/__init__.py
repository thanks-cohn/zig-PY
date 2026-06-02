"""zig-PY v0: build and load a Zig shared library from Python."""

from __future__ import annotations

from .build import build_add_example
from .loader import load_add_library

__all__ = ["build_add_example", "load_add_library"]
__version__ = "0.0.0"
