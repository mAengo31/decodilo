from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class SubprocessRetryReport:
    label: str
    reason: str
    attempts_allowed: int
    attempts_run: int
    passed: bool
    first_failure_summary: str | None
    final_result: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


def run_bounded_subprocess_retry(
    *,
    label: str,
    reason: str,
    attempts: int,
    base_tmp_path: Path,
    run_attempt: Callable[[Path], T],
) -> tuple[T, SubprocessRetryReport]:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    first_failure_summary: str | None = None
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        attempt_dir = base_tmp_path / f"attempt-{attempt}"
        attempt_dir.mkdir(parents=True, exist_ok=False)
        try:
            result = run_attempt(attempt_dir)
        except Exception as exc:  # noqa: BLE001 - pytest helper reports arbitrary failures
            last_error = exc
            if first_failure_summary is None:
                first_failure_summary = f"{type(exc).__name__}: {str(exc)[:500]}"
            continue
        return result, SubprocessRetryReport(
            label=label,
            reason=reason,
            attempts_allowed=attempts,
            attempts_run=attempt,
            passed=True,
            first_failure_summary=first_failure_summary,
            final_result="passed",
        )

    report = SubprocessRetryReport(
        label=label,
        reason=reason,
        attempts_allowed=attempts,
        attempts_run=attempts,
        passed=False,
        first_failure_summary=first_failure_summary,
        final_result="failed_all_attempts",
    )
    raise AssertionError(report.to_json()) from last_error
