from __future__ import annotations

from lambda_m081s_helpers import make_m081r_artifact_capture_blocked_workdir, write_m081r_manifest

from decodilo.lambda_cloud.diloco_smoke_attempt_closeout import (
    build_lambda_diloco_smoke_attempt_closeout_from_paths,
    write_lambda_diloco_smoke_attempt_closeout,
)
from decodilo.lambda_cloud.m081r2_diloco_synthetic_authorization import (
    build_lambda_m081r2_diloco_synthetic_authorization_from_paths,
    write_lambda_m081r2_diloco_synthetic_authorization,
)
from decodilo.lambda_cloud.m081r2_diloco_synthetic_runbook_preview import (
    build_lambda_m081r2_diloco_synthetic_runbook_preview_from_paths,
)
from decodilo.lambda_cloud.m081r_diloco_synthetic_authorization import (
    LambdaM081RDilocoSyntheticAuthorization,
    write_lambda_m081r_diloco_synthetic_authorization,
)
from decodilo.lambda_cloud.remote_vslice_manifest_artifact_capture import (
    build_lambda_remote_vslice_manifest_artifact_policy_from_path,
    write_lambda_remote_vslice_manifest_artifact_policy,
)


def test_m081r2_runbook_preview_is_ready_and_non_executable(tmp_path):
    closeout_path = tmp_path / "closeout.json"
    policy_path = tmp_path / "policy.json"
    previous_path = tmp_path / "previous.json"
    authorization_path = tmp_path / "authorization.json"
    write_lambda_diloco_smoke_attempt_closeout(
        closeout_path,
        build_lambda_diloco_smoke_attempt_closeout_from_paths(
            workdir=make_m081r_artifact_capture_blocked_workdir(tmp_path),
        ),
    )
    write_lambda_remote_vslice_manifest_artifact_policy(
        policy_path,
        build_lambda_remote_vslice_manifest_artifact_policy_from_path(
            manifest=write_m081r_manifest(tmp_path / "manifest.json"),
        ),
    )
    write_lambda_m081r_diloco_synthetic_authorization(
        previous_path,
        LambdaM081RDilocoSyntheticAuthorization(
            authorization_status="authorized_for_future_m081r_diloco_synthetic_experiment",
            command_category="dev_diloco_smoke_one_step",
        ),
    )
    write_lambda_m081r2_diloco_synthetic_authorization(
        authorization_path,
        build_lambda_m081r2_diloco_synthetic_authorization_from_paths(
            attempt_closeout=closeout_path,
            manifest_artifact_policy=policy_path,
            previous_authorization=previous_path,
        ),
    )

    preview = build_lambda_m081r2_diloco_synthetic_runbook_preview_from_paths(
        authorization=authorization_path,
        manifest_artifact_policy=policy_path,
    )

    assert preview.preview_status == "ready_for_future_m081r2_diloco_synthetic_retry_review"
    assert preview.executable is False
    assert preview.capture_declared_artifact_on_success_or_failure is True
    assert preview.no_arbitrary_file_reads is True
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
