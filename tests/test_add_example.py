from __future__ import annotations

import subprocess
import sys

from zig_py.build import build_add_example
from zig_py.loader import load_add_library


def test_add_example_builds_loads_and_returns_five() -> None:
    build = build_add_example()
    library = load_add_library(build.library_path)
    assert library.add(2, 3) == 5


def test_add_example_script_calls_zig_successfully() -> None:
    build_add_example()
    completed = subprocess.run(
        [sys.executable, "examples/add/run.py"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert completed.returncode == 0, completed.stdout
    assert "Python successfully called Zig" in completed.stdout
