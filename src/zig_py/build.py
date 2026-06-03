"""Build Zig examples into shared libraries."""

from __future__ import annotations

import argparse
import json
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

VALID_OPTIMIZE_MODES = ("Debug", "ReleaseSafe", "ReleaseFast", "ReleaseSmall")
DEFAULT_OPTIMIZE_MODE = "ReleaseFast"


@dataclass(frozen=True)
class BuildResult:
    library_path: Path
    log_path: Path
    command: list[str]
    rebuilt: bool
    elapsed_seconds: float
    optimize_mode: str


def shared_library_name(stem: str) -> str:
    system = platform.system()
    if system == "Windows":
        return f"{stem}.dll"
    if system == "Darwin":
        return f"lib{stem}.dylib"
    return f"lib{stem}.so"


def _metadata_path(library_path: Path) -> Path:
    return library_path.with_suffix(f"{library_path.suffix}.build.json")


def _read_build_metadata(metadata_path: Path) -> dict[str, object]:
    if not metadata_path.exists():
        return {}
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _write_build_metadata(metadata_path: Path, *, source_path: Path, optimize_mode: str) -> None:
    metadata_path.write_text(
        json.dumps(
            {
                "source": str(source_path),
                "optimize_mode": optimize_mode,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _is_output_current(source_path: Path, library_path: Path, *, optimize_mode: str) -> bool:
    if not library_path.exists():
        return False
    metadata = _read_build_metadata(_metadata_path(library_path))
    if metadata.get("optimize_mode") != optimize_mode:
        return False
    return source_path.stat().st_mtime <= library_path.stat().st_mtime


def _write_log(log_path: Path, lines: list[str], command_output: str = "") -> None:
    body = "\n".join(lines)
    if command_output:
        body = f"{body}\n\n--- command output ---\n{command_output}"
    log_path.write_text(f"{body.rstrip()}\n", encoding="utf-8")


def build_add_example(*, force: bool = False, optimize_mode: str = DEFAULT_OPTIMIZE_MODE) -> BuildResult:
    if optimize_mode not in VALID_OPTIMIZE_MODES:
        choices = ", ".join(VALID_OPTIMIZE_MODES)
        raise ValueError(f"optimize_mode must be one of: {choices}")

    log.info(f"building Zig add example from {ADD_SOURCE}")
    log.info(f"using Zig optimization mode: {optimize_mode}")
    zig = shutil.which("zig")

    output_dir = BUILD_ROOT / "add"
    output_dir.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    library_path = output_dir / shared_library_name("add")
    log_path = LOG_ROOT / "add-build.log"
    metadata_path = _metadata_path(library_path)
    command = [
        zig or "zig",
        "build-lib",
        str(ADD_SOURCE),
        "-dynamic",
        "-O",
        optimize_mode,
        f"-femit-bin={library_path}",
    ]

    start = time.perf_counter()
    source_mtime = ADD_SOURCE.stat().st_mtime
    library_mtime = library_path.stat().st_mtime if library_path.exists() else None
    if not force and _is_output_current(ADD_SOURCE, library_path, optimize_mode=optimize_mode):
        elapsed = time.perf_counter() - start
        log.ok(f"skipping Zig build because {library_path} is current")
        log.info(f"build freshness check completed in {elapsed:.3f}s")
        _write_log(
            log_path,
            [
                "zig-PY add example build skipped",
                f"reason: output is current (source mtime {source_mtime:.6f} <= output mtime {library_mtime:.6f})",
                f"elapsed_seconds: {elapsed:.6f}",
                f"optimize_mode: {optimize_mode}",
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
            optimize_mode=optimize_mode,
        )

    if zig is None:
        log.error("cannot build because zig was not found on PATH")
        log.fix("Install Zig from https://ziglang.org/download/ and rerun make doctor.")
        raise SystemExit(MISSING_ZIG)

    if force:
        log.info("--force supplied; rebuilding even if the output library is current")
    else:
        metadata = _read_build_metadata(metadata_path)
        previous_optimize_mode = metadata.get("optimize_mode", "unknown")
        if library_path.exists() and previous_optimize_mode != optimize_mode:
            log.info(
                f"rebuilding because optimization mode changed from {previous_optimize_mode} to {optimize_mode}"
            )
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
            f"optimize_mode: {optimize_mode}",
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
    _write_build_metadata(metadata_path, source_path=ADD_SOURCE, optimize_mode=optimize_mode)
    log.ok(f"built shared library at {library_path}")
    log.ok(f"build log written to {log_path}")
    return BuildResult(
        library_path=library_path,
        log_path=log_path,
        command=command,
        rebuilt=True,
        elapsed_seconds=elapsed,
        optimize_mode=optimize_mode,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build zig-PY examples.")
    parser.add_argument("--example", choices=["add"], default="add", help="example to build")
    parser.add_argument("--force", action="store_true", help="rebuild even when the output library is current")
    parser.add_argument(
        "--optimize",
        choices=VALID_OPTIMIZE_MODES,
        default=DEFAULT_OPTIMIZE_MODE,
        help=f"Zig optimization mode (default: {DEFAULT_OPTIMIZE_MODE})",
    )
    args = parser.parse_args(argv)
    build_add_example(force=args.force, optimize_mode=args.optimize)
    return SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
