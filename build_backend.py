"""Tiny dependency-free build backend for zig-PY v0.

It builds a pure-Python wheel and an editable wheel that adds ./src to
PYTHONPATH through a .pth file. This keeps `pip install -e ".[dev]"` usable in
minimal Python environments without downloading a build backend first.
"""

from __future__ import annotations

import base64
import hashlib
import os
import zipfile
from pathlib import Path

NAME = "zig-PY"
DIST = "zig_py"
VERSION = "0.0.0"
DIST_INFO = f"{DIST}-{VERSION}.dist-info"


def _metadata() -> str:
    readme = Path("README.md").read_text(encoding="utf-8")
    return "\n".join(
        [
            "Metadata-Version: 2.1",
            f"Name: {NAME}",
            f"Version: {VERSION}",
            "Summary: Small Python-to-Zig shared-library bridge foundation.",
            "Requires-Python: >=3.9",
            "Provides-Extra: dev",
            "Requires-Dist: pytest>=8; extra == 'dev'",
            "Description-Content-Type: text/markdown",
            "",
            readme,
        ]
    )


def _wheel() -> str:
    return "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: zig-PY build_backend.py",
            "Root-Is-Purelib: true",
            "Tag: py3-none-any",
            "",
        ]
    )


def _hash(data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
    return f"sha256={digest}"


def _write_wheel(wheel_directory: str, files: dict[str, bytes]) -> str:
    wheel_name = f"{DIST}-{VERSION}-py3-none-any.whl"
    wheel_path = Path(wheel_directory) / wheel_name
    records: list[tuple[str, str, int | str]] = []
    timestamp = (2026, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for archive_name, data in files.items():
            info = zipfile.ZipInfo(archive_name, timestamp)
            zf.writestr(info, data)
            records.append((archive_name, _hash(data), len(data)))
        record_name = f"{DIST_INFO}/RECORD"
        record_lines = [f"{path},{digest},{size}" for path, digest, size in records]
        record_lines.append(f"{record_name},,")
        record_data = ("\n".join(record_lines) + "\n").encode("utf-8")
        info = zipfile.ZipInfo(record_name, timestamp)
        zf.writestr(info, record_data)
    return wheel_name


def _entry_points() -> str:
    return "\n".join(
        [
            "[console_scripts]",
            "zig-py-doctor = zig_py.doctor:main",
            "zig-py-build-example = zig_py.build:main",
            "",
        ]
    )


def _dist_info_files() -> dict[str, bytes]:
    return {
        f"{DIST_INFO}/METADATA": _metadata().encode("utf-8"),
        f"{DIST_INFO}/WHEEL": _wheel().encode("utf-8"),
        f"{DIST_INFO}/entry_points.txt": _entry_points().encode("utf-8"),
    }


def build_wheel(wheel_directory: str, config_settings=None, metadata_directory: str | None = None) -> str:
    files = _dist_info_files()
    for path in Path("src").rglob("*.py"):
        files[path.relative_to("src").as_posix()] = path.read_bytes()
    return _write_wheel(wheel_directory, files)


def build_editable(wheel_directory: str, config_settings=None, metadata_directory: str | None = None) -> str:
    files = _dist_info_files()
    src_path = (Path.cwd() / "src").resolve()
    files[f"{DIST}.pth"] = f"{src_path}{os.linesep}".encode("utf-8")
    return _write_wheel(wheel_directory, files)


def get_requires_for_build_wheel(config_settings=None) -> list[str]:
    return []


def get_requires_for_build_editable(config_settings=None) -> list[str]:
    return []


def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings=None) -> str:
    path = Path(metadata_directory) / DIST_INFO
    path.mkdir(parents=True, exist_ok=True)
    (path / "METADATA").write_text(_metadata(), encoding="utf-8")
    (path / "WHEEL").write_text(_wheel(), encoding="utf-8")
    return DIST_INFO


def prepare_metadata_for_build_editable(metadata_directory: str, config_settings=None) -> str:
    return prepare_metadata_for_build_wheel(metadata_directory, config_settings)
