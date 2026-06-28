from __future__ import annotations

from decodilo.lambda_cloud.m075r2_runtime_smoke_retry_authorization import (
    LambdaM075R2RuntimeSmokeRetryAuthorization,
    write_lambda_m075r2_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.m075r2_runtime_smoke_runbook_preview import (
    build_lambda_m075r2_runtime_smoke_runbook_preview_from_paths,
)
from decodilo.lambda_cloud.remote_vslice_failure_artifact_capture_policy import (
    LambdaRemoteVSliceFailureArtifactCapturePolicy,
    write_lambda_remote_vslice_failure_artifact_capture_policy,
)


def test_m075r2_runbook_preview_is_non_executable_and_mentions_failure_capture(
    tmp_path,
):
    auth = tmp_path / "auth.json"
    capture = tmp_path / "capture.json"
    write_lambda_m075r2_runtime_smoke_retry_authorization(
        auth,
        LambdaM075R2RuntimeSmokeRetryAuthorization(
            authorization_status="authorized_for_future_m075r2_runtime_smoke_retry",
        ),
    )
    write_lambda_remote_vslice_failure_artifact_capture_policy(
        capture,
        LambdaRemoteVSliceFailureArtifactCapturePolicy(
            policy_passed=True,
            capture_on_failure_allowed=True,
            expected_output_artifact_path="/tmp/decodilo-runtime-smoke.json",
            max_artifact_bytes=32768,
        ),
    )

    preview = build_lambda_m075r2_runtime_smoke_runbook_preview_from_paths(
        authorization=auth,
        failure_artifact_policy=capture,
    )

    assert preview.preview_status == "ready_for_future_m075r2_runtime_smoke_retry_review"
    assert preview.executable is False
    assert any("success or failure" in step for step in preview.required_steps)
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
