from __future__ import annotations

from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_authorization import (
    LambdaM089RBoundedDilocoExperimentAuthorization,
    write_lambda_m089r_bounded_diloco_experiment_authorization,
)
from decodilo.lambda_cloud.m089r_bounded_diloco_experiment_runbook_preview import (
    build_lambda_m089r_bounded_diloco_experiment_runbook_preview_from_path,
)


def test_m089r_runbook_preview_blocks_without_safe_command(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m089r_bounded_diloco_experiment_authorization(
        authorization_path,
        LambdaM089RBoundedDilocoExperimentAuthorization(
            authorization_status="not_authorized",
            blockers=["no_safe_bounded_diloco_experiment_command_found"],
        ),
    )

    report = build_lambda_m089r_bounded_diloco_experiment_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert report.preview_status == "blocked_no_safe_bounded_diloco_experiment_command"
    assert report.executable is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m089r_runbook_preview_ready_when_future_authorized(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m089r_bounded_diloco_experiment_authorization(
        authorization_path,
        LambdaM089RBoundedDilocoExperimentAuthorization(
            authorization_status=(
                "authorized_for_future_m089r_bounded_diloco_experiment"
            ),
            command_category="dev_bounded_diloco_experiment_one_step",
        ),
    )

    report = build_lambda_m089r_bounded_diloco_experiment_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert (
        report.preview_status
        == "ready_for_future_m089r_bounded_diloco_experiment_review"
    )
    assert report.executable is False
    assert any("bounded synthetic DiLoCo" in item for item in report.future_requirements)
    assert report.launch_ready is False
    assert report.launch_allowed is False
