from __future__ import annotations

from decodilo.lambda_cloud.m076a_report import LambdaM076AReport
from decodilo.lambda_cloud.m077r_first_synthetic_experiment_authorization import (
    LambdaM077RFirstSyntheticExperimentAuthorization,
)


def test_m077r_authorization_remains_future_only_after_m076a() -> None:
    authorization = LambdaM077RFirstSyntheticExperimentAuthorization(
        authorization_status="authorized_for_future_m077r_first_synthetic_experiment",
        command_category="dev_synthetic_experiment_one_step",
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m076a_report_keeps_launch_disabled() -> None:
    report = LambdaM076AReport(
        report_passed=True,
        synthetic_experiment_command_added=True,
        discovery_status="found_safe_first_synthetic_experiment_command",
        selected_command=[
            "env",
            "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
            "python3",
            "-m",
            "decodilo.cli",
            "dev",
            "synthetic-experiment",
            "--synthetic",
            "--max-steps",
            "1",
            "--out",
            "/tmp/decodilo-synthetic-experiment.json",
        ],
        policy_status="policy_passed",
        m077r_authorization_status=(
            "authorized_for_future_m077r_first_synthetic_experiment"
        ),
        runbook_preview_status=(
            "ready_for_future_m077r_first_synthetic_experiment_review"
        ),
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
