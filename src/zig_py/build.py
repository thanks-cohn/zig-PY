"""Build Zig examples into shared libraries."""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import logging as log

SUCCESS = 0
MISSING_ZIG = 10
BUILD_FAILURE = 20

REPO_ROOT = Path(__file__).resolve().parents[2]
ADD_SOURCE = REPO_ROOT / "examples" / "add" / "add.zig"
BUILD_ROOT = REPO_ROOT / "build" / "zig_py"
LOG_ROOT = REPO_ROOT / "build" / "logs"


@dataclass(frozen=True)
class BuildResult:
    library_path: Path
    log_path: Path
    command: list[str]


def shared_library_name(stem: str) -> str:
    system = platform.system()
    if system == "Windows":
        return f"{stem}.dll"
    if system == "Darwin":
        return f"lib{stem}.dylib"
    return f"lib{stem}.so"


def build_add_example() -> BuildResult:
    log.info(f"building Zig add example from {ADD_SOURCE}")
    zig = shutil.which("zig")
    if zig is None:
        log.error("cannot build because zig was not found on PATH")
        log.fix("Install Zig from https://ziglang.org/download/ and rerun make doctor.")
        raise SystemExit(MISSING_ZIG)

    output_dir = BUILD_ROOT / "add"
    output_dir.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    library_path = output_dir / shared_library_name("add")
    log_path = LOG_ROOT / "add-build.log"
    command = [
        zig,
        "build-lib",
        str(ADD_SOURCE),
        "-dynamic",
        "-O",
        "ReleaseSafe",
        f"-femit-bin={library_path}",
    ]
    log.command(command, cwd=REPO_ROOT, output=log_path)
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log_path.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        log.error(f"Zig build failed with exit code {completed.returncode}; output is in {log_path}")
        log.fix("Open the build log, fix the Zig compiler error, then rerun make build-example.")
        raise SystemExit(BUILD_FAILURE)
    if not library_path.exists():
        log.error(f"Zig reported success but expected library is missing: {library_path}")
        log.fix("Check the Zig version and build log, then rerun make build-example.")
        raise SystemExit(BUILD_FAILURE)
    log.ok(f"built shared library at {library_path}")
    log.ok(f"build log written to {log_path}")
    return BuildResult(library_path=library_path, log_path=log_path, command=command)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build zig-PY examples.")
    parser.add_argument("--example", choices=["add"], default="add", help="example to build")
    parser.parse_args(argv)
    build_add_example()
    return SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
