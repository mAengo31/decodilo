"""Small local flake-audit runner for selected pytest tests."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class FlakeAuditRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    test: str
    attempt: int
    returncode: int
    wall_time_seconds: float = Field(ge=0)
    stdout_tail: str = ""
    stderr_tail: str = ""


class FlakeAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    tests_requested: list[str]
    repeats: int
    failures: list[FlakeAuditRun] = Field(default_factory=list)
    flaky_detected: bool
    slowest_run_seconds: float = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


CommandRunner = Callable[[list[str]], tuple[int, str, str]]


def run_flake_audit(
    *,
    tests: list[str],
    repeat: int,
    command_runner: CommandRunner | None = None,
) -> FlakeAuditReport:
    repeats = max(1, repeat)
    failures: list[FlakeAuditRun] = []
    slowest = 0.0
    runner = command_runner or _run_pytest_command
    for test in tests:
        for attempt in range(1, repeats + 1):
            start = time.monotonic()
            returncode, stdout, stderr = runner(["pytest", "-q", test])
            elapsed = time.monotonic() - start
            slowest = max(slowest, elapsed)
            if returncode != 0:
                failures.append(
                    FlakeAuditRun(
                        test=test,
                        attempt=attempt,
                        returncode=returncode,
                        wall_time_seconds=elapsed,
                        stdout_tail=stdout[-1000:],
                        stderr_tail=stderr[-1000:],
                    )
                )
    failed_tests = {failure.test for failure in failures}
    flaky = any(0 < sum(f.test == test for f in failures) < repeats for test in tests)
    warnings = []
    if failed_tests:
        warnings.append("one or more audited local tests failed")
    if flaky:
        warnings.append("failure pattern is inconsistent across repeats")
    return FlakeAuditReport(
        tests_requested=tests,
        repeats=repeats,
        failures=failures,
        flaky_detected=flaky,
        slowest_run_seconds=slowest,
        warnings=warnings,
    )


def write_flake_audit_report(path: str | Path, report: FlakeAuditReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _run_pytest_command(command: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr
