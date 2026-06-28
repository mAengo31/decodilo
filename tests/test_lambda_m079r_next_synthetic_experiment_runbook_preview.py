from __future__ import annotations

from decodilo.lambda_cloud.m079r_next_synthetic_experiment_authorization import (
    LambdaM079RNextSyntheticExperimentAuthorization,
    write_lambda_m079r_next_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.m079r_next_synthetic_experiment_runbook_preview import (
    build_lambda_m079r_next_synthetic_experiment_runbook_preview_from_path,
)


def test_m079r_runbook_preview_blocks_without_safe_command(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m079r_next_synthetic_experiment_authorization(
        authorization_path,
        LambdaM079RNextSyntheticExperimentAuthorization(
            authorization_status="not_authorized",
            blockers=["no_safe_next_synthetic_experiment_command_found"],
        ),
    )

    preview = build_lambda_m079r_next_synthetic_experiment_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert preview.preview_status == "blocked_no_safe_next_synthetic_experiment_command"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False


def test_m079r_runbook_preview_ready_when_authorized(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m079r_next_synthetic_experiment_authorization(
        authorization_path,
        LambdaM079RNextSyntheticExperimentAuthorization(
            authorization_status=(
                "authorized_for_future_m079r_next_synthetic_experiment"
            ),
            command_category="dev_learner_syncer_smoke_one_step",
        ),
    )

    preview = build_lambda_m079r_next_synthetic_experiment_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert (
        preview.preview_status
        == "ready_for_future_m079r_next_synthetic_experiment_review"
    )
    assert "run exactly one bounded synthetic learner/syncer or DiLoCo-shaped command" in (
        preview.future_requirements
    )
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
