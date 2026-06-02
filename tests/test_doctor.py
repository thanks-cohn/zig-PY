from __future__ import annotations

from zig_py import doctor


def test_doctor_reports_platform_and_python() -> None:
    results = doctor.run_checks()
    names = {result.name for result in results}
    assert {"python", "zig", "pytest", "platform"} <= names
    assert next(result for result in results if result.name == "python").ok
    assert next(result for result in results if result.name == "platform").ok


def test_doctor_exit_code_prioritizes_missing_zig() -> None:
    results = [
        doctor.CheckResult("zig", False, "missing"),
        doctor.CheckResult("pytest", False, "missing"),
    ]
    assert doctor.exit_code(results) == doctor.MISSING_ZIG


def test_doctor_exit_code_reports_missing_python_dependency() -> None:
    results = [
        doctor.CheckResult("zig", True, "ok"),
        doctor.CheckResult("pytest", False, "missing"),
    ]
    assert doctor.exit_code(results) == doctor.MISSING_PYTHON_DEPENDENCY
