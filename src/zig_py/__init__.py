"""zig-PY v0: build and load a Zig shared library from Python."""

from __future__ import annotations

__all__ = ["build_add_example", "load_add_library"]
__version__ = "0.0.0"


def __getattr__(name: str):
    if name == "build_add_example":
        from .build import build_add_example

        return build_add_example
    if name == "load_add_library":
        from .loader import load_add_library

        return load_add_library
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
