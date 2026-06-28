from __future__ import annotations

from decodilo.lambda_cloud.m084a_report import LambdaM084AReport
from decodilo.lambda_cloud.m085r_integrated_diloco_authorization import (
    LambdaM085RIntegratedDilocoAuthorization,
)


def test_m085r_authorization_remains_future_only_after_m084a() -> None:
    authorization = LambdaM085RIntegratedDilocoAuthorization(
        authorization_status="authorized_for_future_m085r_integrated_diloco_smoke",
        command_category="dev_integrated_diloco_smoke_one_step",
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m084a_report_keeps_launch_disabled() -> None:
    report = LambdaM084AReport(
        report_passed=True,
        integrated_diloco_smoke_command_added=True,
        discovery_status="found_safe_integrated_diloco_command",
        selected_command=[
            "env",
            "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
            "python3",
            "-m",
            "decodilo.cli",
            "dev",
            "integrated-diloco-smoke",
            "--synthetic",
            "--learners",
            "1",
            "--sync-rounds",
            "1",
            "--inner-optimizer",
            "adamw",
            "--outer-optimizer",
            "nesterov",
            "--max-steps",
            "1",
            "--out",
            "/tmp/decodilo-integrated-diloco-smoke.json",
        ],
        policy_status="policy_passed",
        m085r_authorization_status="authorized_for_future_m085r_integrated_diloco_smoke",
        runbook_preview_status="ready_for_future_m085r_integrated_diloco_review",
        integrated_fidelity_status="integrated_optimizer_protocol_smoke",
        learners=1,
        sync_rounds=1,
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
