from __future__ import annotations

from decodilo.lambda_cloud.m082a_report import LambdaM082AReport
from decodilo.lambda_cloud.m083r_diloco_optimizer_authorization import (
    LambdaM083RDilocoOptimizerAuthorization,
)


def test_m083r_authorization_remains_future_only_after_m082a() -> None:
    authorization = LambdaM083RDilocoOptimizerAuthorization(
        authorization_status="authorized_for_future_m083r_diloco_optimizer_smoke",
        command_category="dev_diloco_optimizer_smoke_adamw_nesterov_one_step",
    )

    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False


def test_m082a_report_keeps_launch_disabled() -> None:
    report = LambdaM082AReport(
        report_passed=True,
        diloco_optimizer_smoke_command_added=True,
        discovery_status="found_safe_diloco_optimizer_command",
        selected_command=[
            "env",
            "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
            "python3",
            "-m",
            "decodilo.cli",
            "dev",
            "diloco-optimizer-smoke",
            "--synthetic",
            "--inner-optimizer",
            "adamw",
            "--outer-optimizer",
            "nesterov",
            "--max-steps",
            "1",
            "--out",
            "/tmp/decodilo-diloco-optimizer-smoke.json",
        ],
        policy_status="policy_passed",
        m083r_authorization_status=(
            "authorized_for_future_m083r_diloco_optimizer_smoke"
        ),
        runbook_preview_status="ready_for_future_m083r_diloco_optimizer_review",
        optimizer_fidelity_status="optimizer_semantics_smoke",
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
