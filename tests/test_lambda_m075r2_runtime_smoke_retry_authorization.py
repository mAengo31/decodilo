from __future__ import annotations

from lambda_m075s_helpers import (
    make_m075r_manifest,
    make_m075r_runtime_smoke_failure_workdir,
    make_runtime_authorization,
)

from decodilo.lambda_cloud.m075r2_runtime_smoke_retry_authorization import (
    build_lambda_m075r2_runtime_smoke_retry_authorization_from_paths,
)
from decodilo.lambda_cloud.remote_vslice_expected_artifact_policy import (
    build_lambda_remote_vslice_expected_artifact_policy_from_path,
    write_lambda_remote_vslice_expected_artifact_policy,
)
from decodilo.lambda_cloud.remote_vslice_failure_artifact_capture_policy import (
    build_lambda_remote_vslice_failure_artifact_capture_policy_from_paths,
    write_lambda_remote_vslice_failure_artifact_capture_policy,
)
from decodilo.lambda_cloud.runtime_smoke_failure_closeout import (
    build_lambda_runtime_smoke_failure_closeout_from_path,
    write_lambda_runtime_smoke_failure_closeout,
)
from decodilo.lambda_cloud.runtime_smoke_failure_evidence_policy import (
    build_lambda_runtime_smoke_failure_evidence_policy,
    write_lambda_runtime_smoke_failure_evidence_policy,
)
from decodilo.lambda_cloud.runtime_smoke_failure_record import (
    build_lambda_runtime_smoke_failure_record_from_paths,
    write_lambda_runtime_smoke_failure_record,
)


def test_m075r2_authorization_is_future_only_when_failure_capture_policy_passes(
    tmp_path,
):
    workdir = make_m075r_runtime_smoke_failure_workdir(tmp_path)
    record_path = tmp_path / "failure-record.json"
    closeout_path = tmp_path / "failure-closeout.json"
    artifact_policy_path = tmp_path / "artifact-policy.json"
    failure_policy_path = tmp_path / "failure-policy.json"
    capture_policy_path = tmp_path / "capture-policy.json"
    runtime_auth_path = make_runtime_authorization(tmp_path / "runtime-auth.json")
    write_lambda_runtime_smoke_failure_record(
        record_path,
        build_lambda_runtime_smoke_failure_record_from_paths(workdir=workdir),
    )
    write_lambda_runtime_smoke_failure_closeout(
        closeout_path,
        build_lambda_runtime_smoke_failure_closeout_from_path(
            failure_record=record_path,
        ),
    )
    write_lambda_remote_vslice_expected_artifact_policy(
        artifact_policy_path,
        build_lambda_remote_vslice_expected_artifact_policy_from_path(
            manifest=make_m075r_manifest(tmp_path / "manifest.json"),
        ),
    )
    write_lambda_runtime_smoke_failure_evidence_policy(
        failure_policy_path,
        build_lambda_runtime_smoke_failure_evidence_policy(),
    )
    write_lambda_remote_vslice_failure_artifact_capture_policy(
        capture_policy_path,
        build_lambda_remote_vslice_failure_artifact_capture_policy_from_paths(
            expected_artifact_policy=artifact_policy_path,
            failure_evidence_policy=failure_policy_path,
        ),
    )

    authorization = build_lambda_m075r2_runtime_smoke_retry_authorization_from_paths(
        failure_closeout=closeout_path,
        failure_artifact_policy=capture_policy_path,
        runtime_authorization=runtime_auth_path,
    )

    assert authorization.authorization_status == (
        "authorized_for_future_m075r2_runtime_smoke_retry"
    )
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
