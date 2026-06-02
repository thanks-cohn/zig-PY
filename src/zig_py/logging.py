"""Small stdout logger used by zig-PY commands."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Iterable, TextIO


def _line(prefix: str, message: str, *, stream: TextIO = sys.stdout) -> None:
    print(f"zig-PY {prefix} {message}", file=stream, flush=True)


def info(message: str) -> None:
    _line("INFO", message)


def ok(message: str) -> None:
    _line("OK", message)


def error(message: str) -> None:
    _line("ERROR", message, stream=sys.stderr)


def fix(message: str) -> None:
    _line("FIX", message, stream=sys.stderr)


def command(argv: Iterable[str], *, cwd: Path | None = None, output: Path | None = None) -> None:
    rendered = " ".join(shlex.quote(part) for part in argv)
    if cwd is not None:
        info(f"running command from {cwd}: {rendered}")
    else:
        info(f"running command: {rendered}")
    if output is not None:
        info(f"command output will be written to {output}")
