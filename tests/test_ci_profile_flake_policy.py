from __future__ import annotations

from decodilo.runtime.flake_policy import build_flake_policy_report


def test_flake_policy_disallows_silent_ignores() -> None:
    report = build_flake_policy_report()

    assert report.policy_status == "active"
    assert report.silent_ignore_allowed is False
    assert report.quick_excludes_subprocess_heavy is True
    assert report.subprocess_recovery_tests_excluded_from_quick is True
    assert report.bounded_retry_requires_reporting is True
    assert "bounded_retry_with_explicit_reporting" in report.allowed_resolutions
    assert "hide_by_over_broad_deselection" in report.disallowed_resolutions


def test_flake_policy_cannot_enable_cloud_launch() -> None:
    report = build_flake_policy_report()

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False
