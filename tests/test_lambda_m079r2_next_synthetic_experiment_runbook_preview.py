from __future__ import annotations

from lambda_m079s_helpers import write_m079r_manifest

from decodilo.lambda_cloud.m079r2_next_synthetic_experiment_authorization import (
    LambdaM079R2NextSyntheticExperimentAuthorization,
    write_lambda_m079r2_next_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.m079r2_next_synthetic_experiment_runbook_preview import (
    build_lambda_m079r2_next_synthetic_experiment_runbook_preview_from_paths,
)
from decodilo.lambda_cloud.remote_vslice_declared_artifact_policy import (
    build_lambda_remote_vslice_declared_artifact_policy_from_path,
    write_lambda_remote_vslice_declared_artifact_policy,
)


def test_m079r2_runbook_preview_ready_and_non_executable(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    policy_path = tmp_path / "policy.json"
    write_lambda_m079r2_next_synthetic_experiment_authorization(
        authorization_path,
        LambdaM079R2NextSyntheticExperimentAuthorization(
            authorization_status=(
                "authorized_for_future_m079r2_next_synthetic_experiment_retry"
            ),
            reason="retry_with_manifest_declared_artifact_capture_fixed",
        ),
    )
    write_lambda_remote_vslice_declared_artifact_policy(
        policy_path,
        build_lambda_remote_vslice_declared_artifact_policy_from_path(
            manifest=write_m079r_manifest(tmp_path / "manifest.json"),
        ),
    )

    preview = build_lambda_m079r2_next_synthetic_experiment_runbook_preview_from_paths(
        authorization=authorization_path,
        declared_artifact_policy=policy_path,
    )

    assert (
        preview.preview_status
        == "ready_for_future_m079r2_next_synthetic_experiment_retry_review"
    )
    assert preview.executable is False
    assert preview.capture_declared_artifact_on_success_or_failure is True
    assert preview.no_arbitrary_file_reads is True
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
