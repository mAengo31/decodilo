from __future__ import annotations

from lambda_m075s_helpers import (
    make_m075r2_runtime_smoke_metadata_workdir,
    make_m075r_manifest,
)

from decodilo.lambda_cloud.m075r2_runtime_smoke_retry_authorization import (
    LambdaM075R2RuntimeSmokeRetryAuthorization,
    write_lambda_m075r2_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.m075r3_runtime_smoke_retry_authorization import (
    build_lambda_m075r3_runtime_smoke_retry_authorization_from_paths,
)
from decodilo.lambda_cloud.remote_vslice_expected_artifact_policy import (
    build_lambda_remote_vslice_expected_artifact_policy_from_path,
    write_lambda_remote_vslice_expected_artifact_policy,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_body_policy import (
    build_lambda_runtime_smoke_artifact_body_policy_from_path,
    write_lambda_runtime_smoke_artifact_body_policy,
)
from decodilo.lambda_cloud.runtime_smoke_attempt_closeout import (
    build_lambda_runtime_smoke_attempt_closeout_from_paths,
    write_lambda_runtime_smoke_attempt_closeout,
)


def test_m075r3_authorization_is_future_only_with_body_policy(tmp_path):
    workdir = make_m075r2_runtime_smoke_metadata_workdir(tmp_path)
    closeout_path = tmp_path / "closeout.json"
    write_lambda_runtime_smoke_attempt_closeout(
        closeout_path,
        build_lambda_runtime_smoke_attempt_closeout_from_paths(workdir=workdir),
    )
    manifest = make_m075r_manifest(tmp_path / "manifest.json")
    expected_path = tmp_path / "expected.json"
    write_lambda_remote_vslice_expected_artifact_policy(
        expected_path,
        build_lambda_remote_vslice_expected_artifact_policy_from_path(
            manifest=manifest,
        ),
    )
    body_policy_path = tmp_path / "body-policy.json"
    write_lambda_runtime_smoke_artifact_body_policy(
        body_policy_path,
        build_lambda_runtime_smoke_artifact_body_policy_from_path(
            expected_artifact_policy=expected_path,
        ),
    )
    previous_path = tmp_path / "previous.json"
    write_lambda_m075r2_runtime_smoke_retry_authorization(
        previous_path,
        LambdaM075R2RuntimeSmokeRetryAuthorization(
            authorization_status="authorized_for_future_m075r2_runtime_smoke_retry"
        ),
    )

    authorization = build_lambda_m075r3_runtime_smoke_retry_authorization_from_paths(
        attempt_closeout=closeout_path,
        artifact_body_policy=body_policy_path,
        previous_authorization=previous_path,
    )

    assert authorization.authorization_status == (
        "authorized_for_future_m075r3_runtime_smoke_retry"
    )
    assert authorization.reason == "retry_with_declared_artifact_body_or_summary_capture"
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
