from __future__ import annotations

from decodilo.lambda_cloud.m078a_report import LambdaM078AReport
from decodilo.lambda_cloud.m079r_next_synthetic_experiment_authorization import (
    LambdaM079RNextSyntheticExperimentAuthorization,
)


def test_m079r_authorization_remains_future_only_after_m078a() -> None:
    authorization = LambdaM079RNextSyntheticExperimentAuthorization(
        authorization_status="authorized_for_future_m079r_next_synthetic_experiment",
        command_category="dev_learner_syncer_smoke_one_step",
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m078a_report_keeps_launch_disabled() -> None:
    report = LambdaM078AReport(
        report_passed=True,
        learner_syncer_smoke_command_added=True,
        discovery_status="found_safe_next_synthetic_experiment_command",
        selected_command=[
            "env",
            "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
            "python3",
            "-m",
            "decodilo.cli",
            "dev",
            "learner-syncer-smoke",
            "--synthetic",
            "--max-steps",
            "1",
            "--out",
            "/tmp/decodilo-learner-syncer-smoke.json",
        ],
        policy_status="policy_passed",
        m079r_authorization_status=(
            "authorized_for_future_m079r_next_synthetic_experiment"
        ),
        runbook_preview_status=(
            "ready_for_future_m079r_next_synthetic_experiment_review"
        ),
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
