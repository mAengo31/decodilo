from __future__ import annotations

from decodilo.lambda_cloud.m081r_diloco_synthetic_authorization import (
    LambdaM081RDilocoSyntheticAuthorization,
    write_lambda_m081r_diloco_synthetic_authorization,
)
from decodilo.lambda_cloud.m081r_diloco_synthetic_runbook_preview import (
    build_lambda_m081r_diloco_synthetic_runbook_preview_from_path,
)


def test_m081r_runbook_preview_blocks_without_command(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m081r_diloco_synthetic_authorization(
        authorization_path,
        LambdaM081RDilocoSyntheticAuthorization(
            authorization_status="not_authorized",
            blockers=["no_safe_diloco_synthetic_command_found"],
        ),
    )

    preview = build_lambda_m081r_diloco_synthetic_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert preview.preview_status == "blocked_no_safe_diloco_synthetic_command"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False


def test_m081r_runbook_preview_ready_when_future_authorized(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m081r_diloco_synthetic_authorization(
        authorization_path,
        LambdaM081RDilocoSyntheticAuthorization(
            authorization_status=(
                "authorized_for_future_m081r_diloco_synthetic_experiment"
            ),
            command_category="dev_diloco_smoke_one_learner_one_round",
        ),
    )

    preview = build_lambda_m081r_diloco_synthetic_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert preview.preview_status == "ready_for_future_m081r_diloco_synthetic_review"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
