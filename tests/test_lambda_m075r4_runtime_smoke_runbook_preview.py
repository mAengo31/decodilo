from __future__ import annotations

from decodilo.lambda_cloud.m075r4_runtime_smoke_retry_authorization import (
    LambdaM075R4RuntimeSmokeRetryAuthorization,
    write_lambda_m075r4_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.m075r4_runtime_smoke_runbook_preview import (
    build_lambda_m075r4_runtime_smoke_runbook_preview_from_path,
)


def test_m075r4_runbook_preview_is_future_only(tmp_path):
    auth_path = tmp_path / "authorization.json"
    write_lambda_m075r4_runtime_smoke_retry_authorization(
        auth_path,
        LambdaM075R4RuntimeSmokeRetryAuthorization(
            authorization_status="authorized_for_future_m075r4_runtime_smoke_retry",
            reason="local_update_stream_fix_verified",
            local_update_stream_fix_verified=True,
        ),
    )

    preview = build_lambda_m075r4_runtime_smoke_runbook_preview_from_path(
        authorization=auth_path
    )

    assert preview.preview_status == "ready_for_future_m075r4_runtime_smoke_retry_review"
    assert preview.executable is False
    assert preview.retry_same_runtime_smoke_command is True
    assert preview.capture_declared_artifact_on_success_or_failure is True
    assert preview.no_arbitrary_file_reads is True
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
