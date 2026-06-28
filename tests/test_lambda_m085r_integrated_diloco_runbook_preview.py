from __future__ import annotations

from decodilo.lambda_cloud.m085r_integrated_diloco_authorization import (
    LambdaM085RIntegratedDilocoAuthorization,
    write_lambda_m085r_integrated_diloco_authorization,
)
from decodilo.lambda_cloud.m085r_integrated_diloco_runbook_preview import (
    build_lambda_m085r_integrated_diloco_runbook_preview_from_path,
)


def test_m085r_runbook_preview_ready_for_authorized_integrated_command(tmp_path):
    auth_path = tmp_path / "authorization.json"
    write_lambda_m085r_integrated_diloco_authorization(
        auth_path,
        LambdaM085RIntegratedDilocoAuthorization(
            authorization_status="authorized_for_future_m085r_integrated_diloco_smoke",
            run_now=False,
            command_category="dev_integrated_diloco_smoke_one_step",
        ),
    )

    report = build_lambda_m085r_integrated_diloco_runbook_preview_from_path(
        authorization=auth_path,
    )

    assert report.preview_status == "ready_for_future_m085r_integrated_diloco_review"
    assert report.executable is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m085r_runbook_preview_blocks_without_safe_command(tmp_path):
    auth_path = tmp_path / "authorization.json"
    write_lambda_m085r_integrated_diloco_authorization(
        auth_path,
        LambdaM085RIntegratedDilocoAuthorization(
            authorization_status="not_authorized",
            blockers=["no_safe_integrated_diloco_command_found"],
        ),
    )

    report = build_lambda_m085r_integrated_diloco_runbook_preview_from_path(
        authorization=auth_path,
    )

    assert report.preview_status == "blocked_no_safe_integrated_diloco_command"
    assert report.executable is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
