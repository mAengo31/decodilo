from __future__ import annotations

from decodilo.lambda_cloud.m077r_first_synthetic_experiment_authorization import (
    LambdaM077RFirstSyntheticExperimentAuthorization,
    write_lambda_m077r_first_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.m077r_first_synthetic_experiment_runbook_preview import (
    build_lambda_m077r_first_synthetic_experiment_runbook_preview_from_path,
)


def test_m077r_runbook_preview_blocks_without_safe_command(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m077r_first_synthetic_experiment_authorization(
        authorization_path,
        LambdaM077RFirstSyntheticExperimentAuthorization(
            authorization_status="not_authorized",
            blockers=["no_safe_first_synthetic_experiment_command_found"],
        ),
    )

    preview = build_lambda_m077r_first_synthetic_experiment_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert preview.preview_status == "blocked_no_safe_first_synthetic_experiment_command"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False


def test_m077r_runbook_preview_ready_for_future_authorized_retry(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m077r_first_synthetic_experiment_authorization(
        authorization_path,
        LambdaM077RFirstSyntheticExperimentAuthorization(
            authorization_status=(
                "authorized_for_future_m077r_first_synthetic_experiment"
            ),
            command_category="dev_synthetic_experiment_one_step",
        ),
    )

    preview = build_lambda_m077r_first_synthetic_experiment_runbook_preview_from_path(
        authorization=authorization_path,
    )

    assert (
        preview.preview_status
        == "ready_for_future_m077r_first_synthetic_experiment_review"
    )
    assert "run exactly one bounded synthetic Decodilo experiment command" in (
        preview.future_requirements
    )
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
