from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from zig_py import build as build_module
from zig_py.build import DEFAULT_OPTIMIZE_MODE, build_add_example
from zig_py.loader import load_add_library


def _fake_successful_zig(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append(command)
        emit_arg = next(part for part in command if part.startswith("-femit-bin="))
        library_path = Path(emit_arg.split("=", 1)[1])
        library_path.write_bytes(b"fake shared library")
        return SimpleNamespace(returncode=0, stdout="fake zig built add\n")

    monkeypatch.setattr(build_module.shutil, "which", lambda executable: "/usr/bin/zig")
    monkeypatch.setattr(build_module.subprocess, "run", fake_run)
    return calls


@pytest.fixture()
def isolated_build_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    source_path = tmp_path / "add.zig"
    build_root = tmp_path / "build" / "zig_py"
    log_root = tmp_path / "build" / "logs"
    source_path.write_text("export fn add(a: i32, b: i32) i32 { return a + b; }\n", encoding="utf-8")
    monkeypatch.setattr(build_module, "ADD_SOURCE", source_path)
    monkeypatch.setattr(build_module, "BUILD_ROOT", build_root)
    monkeypatch.setattr(build_module, "LOG_ROOT", log_root)
    return source_path, build_root, log_root


def test_default_build_uses_release_fast(
    isolated_build_paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _source_path, _build_root, _log_root = isolated_build_paths
    calls = _fake_successful_zig(monkeypatch)

    result = build_add_example()

    assert DEFAULT_OPTIMIZE_MODE == "ReleaseFast"
    assert result.optimize_mode == "ReleaseFast"
    assert "-O" in result.command
    assert result.command[result.command.index("-O") + 1] == "ReleaseFast"
    assert calls == [result.command]
    log_text = result.log_path.read_text(encoding="utf-8")
    assert "optimize_mode: ReleaseFast" in log_text


def test_cli_optimize_flag_selects_requested_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: dict[str, object] = {}

    def fake_build_add_example(*, force: bool = False, optimize_mode: str = DEFAULT_OPTIMIZE_MODE) -> object:
        requested["force"] = force
        requested["optimize_mode"] = optimize_mode
        return object()

    monkeypatch.setattr(build_module, "build_add_example", fake_build_add_example)

    exit_code = build_module.main(["--example", "add", "--optimize", "ReleaseSmall"])

    assert exit_code == build_module.SUCCESS
    assert requested == {"force": False, "optimize_mode": "ReleaseSmall"}


def test_first_build_creates_shared_library(
    isolated_build_paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _source_path, _build_root, _log_root = isolated_build_paths
    calls = _fake_successful_zig(monkeypatch)

    result = build_add_example()

    assert result.rebuilt is True
    assert result.library_path.exists()
    assert calls == [result.command]
    assert "build executed" in result.log_path.read_text(encoding="utf-8")
    log_text = result.log_path.read_text(encoding="utf-8")
    assert "elapsed_seconds:" in log_text
    assert "optimize_mode: ReleaseFast" in log_text


def test_second_build_skips_when_output_is_current(
    isolated_build_paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source_path, build_root, _log_root = isolated_build_paths
    calls = _fake_successful_zig(monkeypatch)
    library_path = build_root / "add" / build_module.shared_library_name("add")
    library_path.parent.mkdir(parents=True)
    library_path.write_bytes(b"already built")
    build_module._write_build_metadata(
        build_module._metadata_path(library_path), source_path=source_path, optimize_mode="ReleaseFast"
    )
    now = time.time()
    os.utime(source_path, (now - 20, now - 20))
    os.utime(library_path, (now - 10, now - 10))

    result = build_add_example()

    assert result.rebuilt is False
    assert result.library_path == library_path
    assert calls == []
    log_text = result.log_path.read_text(encoding="utf-8")
    assert "build skipped" in log_text
    assert "output is current" in log_text


def test_changing_optimize_mode_rebuilds_then_same_mode_skips(
    isolated_build_paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _source_path, _build_root, _log_root = isolated_build_paths
    calls = _fake_successful_zig(monkeypatch)

    default_result = build_add_example()
    changed_result = build_add_example(optimize_mode="ReleaseSafe")
    skipped_result = build_add_example(optimize_mode="ReleaseSafe")

    assert default_result.rebuilt is True
    assert changed_result.rebuilt is True
    assert skipped_result.rebuilt is False
    assert len(calls) == 2
    assert calls[0][calls[0].index("-O") + 1] == "ReleaseFast"
    assert calls[1][calls[1].index("-O") + 1] == "ReleaseSafe"
    assert skipped_result.optimize_mode == "ReleaseSafe"
    log_text = skipped_result.log_path.read_text(encoding="utf-8")
    assert "build skipped" in log_text
    assert "optimize_mode: ReleaseSafe" in log_text


def test_force_rebuilds_current_output(
    isolated_build_paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    source_path, build_root, _log_root = isolated_build_paths
    calls = _fake_successful_zig(monkeypatch)
    library_path = build_root / "add" / build_module.shared_library_name("add")
    library_path.parent.mkdir(parents=True)
    library_path.write_bytes(b"already built")
    build_module._write_build_metadata(
        build_module._metadata_path(library_path), source_path=source_path, optimize_mode="ReleaseFast"
    )
    now = time.time()
    os.utime(source_path, (now - 20, now - 20))
    os.utime(library_path, (now - 10, now - 10))

    result = build_add_example(force=True)

    assert result.rebuilt is True
    assert calls == [result.command]
    assert "build executed" in result.log_path.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def built_add_library() -> Path:
    if shutil.which("zig") is None:
        pytest.skip("zig is required to build and load the add example")
    library_path = build_module.BUILD_ROOT / "add" / build_module.shared_library_name("add")
    if not build_module._is_output_current(
        build_module.ADD_SOURCE, library_path, optimize_mode=DEFAULT_OPTIMIZE_MODE
    ):
        build_add_example(optimize_mode=DEFAULT_OPTIMIZE_MODE)
    return library_path


def test_python_calls_zig_add_and_returns_five(built_add_library: Path) -> None:
    if shutil.which("zig") is None and not built_add_library.exists():
        pytest.fail("zig is required to build the add example before loading it")
    library = load_add_library(built_add_library)
    assert library.add(2, 3) == 5


def test_add_example_script_calls_zig_successfully(built_add_library: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "examples/add/run.py"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert completed.returncode == 0, completed.stdout
    assert "Python successfully called Zig" in completed.stdout
