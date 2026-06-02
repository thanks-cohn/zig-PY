"""Environment checks for the zig-PY v0 workflow."""

from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass

from . import logging as log

SUCCESS = 0
MISSING_ZIG = 10
MISSING_PYTHON_DEPENDENCY = 11


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    fix: str | None = None


def check_python() -> CheckResult:
    version = platform.python_version()
    if sys.version_info >= (3, 9):
        return CheckResult("python", True, f"Python {version} at {sys.executable}")
    return CheckResult(
        "python",
        False,
        f"Python {version} is too old at {sys.executable}",
        "Create an environment with Python 3.9 or newer, then run pip install -e \".[dev]\".",
    )


def check_zig() -> CheckResult:
    zig = shutil.which("zig")
    if zig is None:
        return CheckResult(
            "zig",
            False,
            "zig executable was not found on PATH",
            "Install Zig from https://ziglang.org/download/ and ensure the zig executable is on PATH.",
        )
    try:
        completed = subprocess.run(
            [zig, "version"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return CheckResult(
            "zig",
            False,
            f"failed to run '{zig} version': {exc}",
            "Reinstall Zig or fix PATH so `zig version` runs successfully.",
        )
    return CheckResult("zig", True, f"Zig {completed.stdout.strip()} at {zig}")


def check_pytest() -> CheckResult:
    if importlib.util.find_spec("pytest") is None:
        return CheckResult(
            "pytest",
            False,
            "pytest is not importable in this Python environment",
            "Run pip install -e \".[dev]\" from the repository root.",
        )
    return CheckResult("pytest", True, "pytest is importable")


def check_platform() -> CheckResult:
    return CheckResult("platform", True, f"{platform.system()} {platform.machine()}")


def run_checks() -> list[CheckResult]:
    log.info("checking Python, Zig, pytest, and platform")
    return [check_python(), check_zig(), check_pytest(), check_platform()]


def exit_code(results: list[CheckResult]) -> int:
    if any(result.name == "zig" and not result.ok for result in results):
        return MISSING_ZIG
    if any(result.name in {"python", "pytest"} and not result.ok for result in results):
        return MISSING_PYTHON_DEPENDENCY
    return SUCCESS


def report(results: list[CheckResult]) -> None:
    for result in results:
        if result.ok:
            log.ok(f"{result.name}: {result.detail}")
        else:
            log.error(f"{result.name}: {result.detail}")
            if result.fix:
                log.fix(result.fix)


def main() -> int:
    results = run_checks()
    report(results)
    code = exit_code(results)
    if code == SUCCESS:
        log.ok("doctor completed successfully")
    else:
        log.error(f"doctor failed with exit code {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
