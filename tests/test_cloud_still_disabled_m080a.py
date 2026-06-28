from __future__ import annotations

from decodilo.lambda_cloud.m080a_report import LambdaM080AReport
from decodilo.lambda_cloud.m081r_diloco_synthetic_authorization import (
    LambdaM081RDilocoSyntheticAuthorization,
)


def test_m081r_authorization_remains_future_only_after_m080a() -> None:
    authorization = LambdaM081RDilocoSyntheticAuthorization(
        authorization_status="authorized_for_future_m081r_diloco_synthetic_experiment",
        command_category="dev_diloco_smoke_one_learner_one_round",
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m080a_report_keeps_launch_disabled() -> None:
    report = LambdaM080AReport(
        report_passed=True,
        diloco_smoke_command_added=True,
        discovery_status="found_safe_diloco_synthetic_command",
        selected_command=[
            "env",
            "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
            "python3",
            "-m",
            "decodilo.cli",
            "dev",
            "diloco-smoke",
            "--synthetic",
            "--learners",
            "1",
            "--sync-rounds",
            "1",
            "--max-steps",
            "1",
            "--out",
            "/tmp/decodilo-diloco-smoke.json",
        ],
        policy_status="policy_passed",
        m081r_authorization_status=(
            "authorized_for_future_m081r_diloco_synthetic_experiment"
        ),
        runbook_preview_status="ready_for_future_m081r_diloco_synthetic_review",
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
