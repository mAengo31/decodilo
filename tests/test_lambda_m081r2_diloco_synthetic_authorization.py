from __future__ import annotations

from lambda_m081s_helpers import make_m081r_artifact_capture_blocked_workdir, write_m081r_manifest

from decodilo.lambda_cloud.diloco_smoke_attempt_closeout import (
    build_lambda_diloco_smoke_attempt_closeout_from_paths,
    write_lambda_diloco_smoke_attempt_closeout,
)
from decodilo.lambda_cloud.m081r2_diloco_synthetic_authorization import (
    build_lambda_m081r2_diloco_synthetic_authorization_from_paths,
)
from decodilo.lambda_cloud.m081r_diloco_synthetic_authorization import (
    LambdaM081RDilocoSyntheticAuthorization,
    write_lambda_m081r_diloco_synthetic_authorization,
)
from decodilo.lambda_cloud.remote_vslice_manifest_artifact_capture import (
    build_lambda_remote_vslice_manifest_artifact_policy_from_path,
    write_lambda_remote_vslice_manifest_artifact_policy,
)


def test_m081r2_authorization_passes_after_manifest_artifact_fix(tmp_path):
    closeout_path = tmp_path / "closeout.json"
    policy_path = tmp_path / "policy.json"
    previous_path = tmp_path / "previous.json"
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

    report = build_lambda_m081r2_diloco_synthetic_authorization_from_paths(
        attempt_closeout=closeout_path,
        manifest_artifact_policy=policy_path,
        previous_authorization=previous_path,
    )

    assert (
        report.authorization_status
        == "authorized_for_future_m081r2_diloco_synthetic_retry"
    )
    assert report.reason == "retry_with_manifest_declared_diloco_artifact_capture_fixed"
    assert report.run_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
