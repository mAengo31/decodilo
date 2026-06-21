from __future__ import annotations

import pytest
from helpers.subprocess_retry import run_bounded_subprocess_retry

from decodilo.runtime.flake_policy import build_flake_policy_report


def test_flake_policy_tracks_subprocess_recovery_test_and_reporting_rules() -> None:
    report = build_flake_policy_report()

    assert report.recovery_flake_resolution == "prefer_deterministic_event_window"
    assert report.subprocess_recovery_tests_excluded_from_quick is True
    assert report.bounded_retry_requires_reporting is True
    assert (
        "tests/test_local_process_failure.py::test_local_recovery_after_kill"
        in report.known_subprocess_sensitive_tests
    )


def test_flake_policy_recovery_rules_do_not_enable_launch() -> None:
    report = build_flake_policy_report()

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False


def test_subprocess_retry_helper_reports_attempts_and_first_failure(tmp_path) -> None:
    attempts_seen: list[str] = []

    def run_attempt(attempt_dir):
        attempts_seen.append(attempt_dir.name)
        if len(attempts_seen) == 1:
            raise AssertionError("synthetic first failure")
        return "ok"

    result, report = run_bounded_subprocess_retry(
        label="synthetic-subprocess",
        reason="test reporting",
        attempts=3,
        base_tmp_path=tmp_path,
        run_attempt=run_attempt,
    )

    assert result == "ok"
    assert report.attempts_run == 2
    assert report.passed is True
    assert report.first_failure_summary is not None
    assert "synthetic first failure" in report.first_failure_summary


def test_subprocess_retry_helper_fails_after_all_attempts(tmp_path) -> None:
    def run_attempt(attempt_dir):
        raise AssertionError(f"still failing in {attempt_dir.name}")

    with pytest.raises(AssertionError, match="failed_all_attempts"):
        run_bounded_subprocess_retry(
            label="synthetic-subprocess",
            reason="test repeated failure",
            attempts=2,
            base_tmp_path=tmp_path,
            run_attempt=run_attempt,
        )
