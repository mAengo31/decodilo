from __future__ import annotations

from decodilo.lambda_cloud.m075r3_runtime_smoke_retry_authorization import (
    LambdaM075R3RuntimeSmokeRetryAuthorization,
    write_lambda_m075r3_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.m075r3_runtime_smoke_runbook_preview import (
    build_lambda_m075r3_runtime_smoke_runbook_preview_from_paths,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_body_policy import (
    LambdaRuntimeSmokeArtifactBodyPolicy,
    write_lambda_runtime_smoke_artifact_body_policy,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
)


def test_m075r3_runbook_preview_is_non_executable(tmp_path):
    authorization_path = tmp_path / "authorization.json"
    policy_path = tmp_path / "body-policy.json"
    write_lambda_m075r3_runtime_smoke_retry_authorization(
        authorization_path,
        LambdaM075R3RuntimeSmokeRetryAuthorization(
            authorization_status="authorized_for_future_m075r3_runtime_smoke_retry",
            reason="retry_with_declared_artifact_body_or_summary_capture",
        ),
    )
    write_lambda_runtime_smoke_artifact_body_policy(
        policy_path,
        LambdaRuntimeSmokeArtifactBodyPolicy(
            policy_status="policy_defined",
            content_capture_allowed=True,
            raw_content_persist_allowed=True,
        ),
    )

    preview = build_lambda_m075r3_runtime_smoke_runbook_preview_from_paths(
        authorization=authorization_path,
        artifact_body_policy=policy_path,
    )

    assert preview.preview_status == "ready_for_future_m075r3_runtime_smoke_retry_review"
    assert preview.executable is False
    assert preview.declared_artifact_path == RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH
    assert preview.capture_declared_artifact_body_or_summary_on_failure is True
    assert preview.no_arbitrary_file_reads is True
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
