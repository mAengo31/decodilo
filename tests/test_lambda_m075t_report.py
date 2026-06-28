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
    write_lambda_m075r3_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.m075r3_runtime_smoke_runbook_preview import (
    build_lambda_m075r3_runtime_smoke_runbook_preview_from_paths,
    write_lambda_m075r3_runtime_smoke_runbook_preview,
)
from decodilo.lambda_cloud.m075t_report import build_lambda_m075t_report_from_paths
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


def test_m075t_report_passes_for_metadata_closeout_and_m075r3_authorization(tmp_path):
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
    policy_path = tmp_path / "policy.json"
    write_lambda_runtime_smoke_artifact_body_policy(
        policy_path,
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
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m075r3_runtime_smoke_retry_authorization(
        authorization_path,
        build_lambda_m075r3_runtime_smoke_retry_authorization_from_paths(
            attempt_closeout=closeout_path,
            artifact_body_policy=policy_path,
            previous_authorization=previous_path,
        ),
    )
    runbook_path = tmp_path / "runbook.json"
    write_lambda_m075r3_runtime_smoke_runbook_preview(
        runbook_path,
        build_lambda_m075r3_runtime_smoke_runbook_preview_from_paths(
            authorization=authorization_path,
            artifact_body_policy=policy_path,
        ),
    )

    report = build_lambda_m075t_report_from_paths(
        attempt_closeout=closeout_path,
        artifact_body_policy=policy_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.m075r2_closeout_status == (
        "closed_runtime_smoke_command_failed_with_artifact_metadata_captured"
    )
    assert report.artifact_metadata_captured is True
    assert report.body_or_summary_capture_required is True
    assert report.m075r3_authorization_status == (
        "authorized_for_future_m075r3_runtime_smoke_retry"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
