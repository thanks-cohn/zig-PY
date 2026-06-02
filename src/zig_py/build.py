"""Build Zig examples into shared libraries."""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import time
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
    rebuilt: bool
    elapsed_seconds: float


def shared_library_name(stem: str) -> str:
    system = platform.system()
    if system == "Windows":
        return f"{stem}.dll"
    if system == "Darwin":
        return f"lib{stem}.dylib"
    return f"lib{stem}.so"


def _is_output_current(source_path: Path, library_path: Path) -> bool:
    if not library_path.exists():
        return False
    return source_path.stat().st_mtime <= library_path.stat().st_mtime


def _write_log(log_path: Path, lines: list[str], command_output: str = "") -> None:
    body = "\n".join(lines)
    if command_output:
        body = f"{body}\n\n--- command output ---\n{command_output}"
    log_path.write_text(f"{body.rstrip()}\n", encoding="utf-8")


def build_add_example(*, force: bool = False) -> BuildResult:
    log.info(f"building Zig add example from {ADD_SOURCE}")
    zig = shutil.which("zig")

    output_dir = BUILD_ROOT / "add"
    output_dir.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    library_path = output_dir / shared_library_name("add")
    log_path = LOG_ROOT / "add-build.log"
    command = [
        zig or "zig",
        "build-lib",
        str(ADD_SOURCE),
        "-dynamic",
        "-O",
        "ReleaseSafe",
        f"-femit-bin={library_path}",
    ]

    start = time.perf_counter()
    source_mtime = ADD_SOURCE.stat().st_mtime
    library_mtime = library_path.stat().st_mtime if library_path.exists() else None
    if not force and _is_output_current(ADD_SOURCE, library_path):
        elapsed = time.perf_counter() - start
        log.ok(f"skipping Zig build because {library_path} is current")
        log.info(f"build freshness check completed in {elapsed:.3f}s")
        _write_log(
            log_path,
            [
                "zig-PY add example build skipped",
                f"reason: output is current (source mtime {source_mtime:.6f} <= output mtime {library_mtime:.6f})",
                f"elapsed_seconds: {elapsed:.6f}",
                f"source: {ADD_SOURCE}",
                f"output: {library_path}",
                f"command: {' '.join(command)}",
            ],
        )
        log.ok(f"build log written to {log_path}")
        return BuildResult(
            library_path=library_path,
            log_path=log_path,
            command=command,
            rebuilt=False,
            elapsed_seconds=elapsed,
        )

    if zig is None:
        log.error("cannot build because zig was not found on PATH")
        log.fix("Install Zig from https://ziglang.org/download/ and rerun make doctor.")
        raise SystemExit(MISSING_ZIG)

    if force:
        log.info("--force supplied; rebuilding even if the output library is current")
    else:
        log.info(f"rebuilding because {library_path} is missing or older than {ADD_SOURCE}")
    log.command(command, cwd=REPO_ROOT, output=log_path)
    log.info("starting Zig build command")
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    elapsed = time.perf_counter() - start
    log.info(f"finished Zig build command in {elapsed:.3f}s with exit code {completed.returncode}")
    _write_log(
        log_path,
        [
            "zig-PY add example build executed",
            f"elapsed_seconds: {elapsed:.6f}",
            f"exit_code: {completed.returncode}",
            f"source: {ADD_SOURCE}",
            f"output: {library_path}",
            f"command: {' '.join(command)}",
        ],
        completed.stdout,
    )
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
    return BuildResult(
        library_path=library_path,
        log_path=log_path,
        command=command,
        rebuilt=True,
        elapsed_seconds=elapsed,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build zig-PY examples.")
    parser.add_argument("--example", choices=["add"], default="add", help="example to build")
    parser.add_argument("--force", action="store_true", help="rebuild even when the output library is current")
    args = parser.parse_args(argv)
    build_add_example(force=args.force)
    return SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
