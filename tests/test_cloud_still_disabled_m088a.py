from __future__ import annotations

from decodilo.lambda_cloud.m088a_report import LambdaM088AReport
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_authorization import (
    LambdaM089RBoundedDilocoExperimentAuthorization,
)


def test_m088a_future_authorization_cannot_enable_launch():
    authorization = LambdaM089RBoundedDilocoExperimentAuthorization(
        authorization_status="authorized_for_future_m089r_bounded_diloco_experiment",
        command_category="dev_bounded_diloco_experiment_one_step",
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m088a_report_cannot_enable_launch():
    report = LambdaM088AReport(
        report_passed=True,
        bounded_diloco_experiment_command_added=True,
        discovery_status="found_safe_bounded_diloco_experiment_command",
        selected_command=[
            "env",
            "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
            "python3",
            "-m",
            "decodilo.cli",
            "dev",
            "bounded-diloco-experiment",
            "--synthetic",
            "--learners",
            "1",
            "--sync-rounds",
            "1",
            "--fragments",
            "2",
            "--inner-optimizer",
            "adamw",
            "--outer-optimizer",
            "nesterov",
            "--max-steps",
            "1",
            "--out",
            "/tmp/decodilo-bounded-diloco-experiment.json",
        ],
        policy_status="policy_passed",
        m089r_authorization_status=(
            "authorized_for_future_m089r_bounded_diloco_experiment"
        ),
        runbook_preview_status=(
            "ready_for_future_m089r_bounded_diloco_experiment_review"
        ),
        bounded_experiment_status="dev_bounded_diloco_experiment_one_step",
        learners=1,
        sync_rounds=1,
        fragments=2,
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
        max_steps=1,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
