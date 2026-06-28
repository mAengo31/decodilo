from __future__ import annotations

from decodilo.lambda_cloud.m073r2_retry_authorization import (
    LambdaM073R2RetryAuthorization,
    write_lambda_m073r2_retry_authorization,
)
from decodilo.lambda_cloud.m073r2_runbook_preview import (
    build_lambda_m073r2_runbook_preview_from_paths,
)
from decodilo.lambda_cloud.source_bundle_upload_policy import (
    LambdaSourceDependencyUploadPolicy,
    write_lambda_source_dependency_upload_policy,
)


def test_m073r2_runbook_preview_is_non_executable_and_mentions_banner(tmp_path):
    auth = tmp_path / "auth.json"
    policy = tmp_path / "policy.json"
    write_lambda_m073r2_retry_authorization(
        auth,
        LambdaM073R2RetryAuthorization(
            authorization_status="authorized_for_future_m073r2_tiny_smoke_retry",
        ),
    )
    write_lambda_source_dependency_upload_policy(
        policy,
        LambdaSourceDependencyUploadPolicy(upload_policy_status="policy_defined"),
    )

    preview = build_lambda_m073r2_runbook_preview_from_paths(
        authorization=auth,
        upload_policy=policy,
    )

    assert preview.preview_status == "ready_for_future_m073r2_tiny_smoke_retry_review"
    assert preview.executable is False
    assert any("SSH banner readiness" in step for step in preview.required_steps)
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
