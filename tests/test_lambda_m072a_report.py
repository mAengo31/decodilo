from __future__ import annotations

from decodilo.lambda_cloud.m072a_report import build_lambda_m072a_report_from_paths
from decodilo.lambda_cloud.m073r_tiny_smoke_authorization import (
    LambdaM073RTinySmokeAuthorization,
    write_lambda_m073r_tiny_smoke_authorization,
)
from decodilo.lambda_cloud.m073r_tiny_smoke_runbook_preview import (
    LambdaM073RTinySmokeRunbookPreview,
    write_lambda_m073r_tiny_smoke_runbook_preview,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_discovery import (
    LambdaTinyDecodiloSmokeDiscovery,
    write_lambda_tiny_decodilo_smoke_discovery,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_policy import (
    LambdaTinyDecodiloSmokePolicy,
    write_lambda_tiny_decodilo_smoke_policy,
)


def test_m072a_report_passes_for_future_authorized_smoke(tmp_path):
    discovery = tmp_path / "discovery.json"
    policy = tmp_path / "policy.json"
    authorization = tmp_path / "authorization.json"
    preview = tmp_path / "preview.json"
    write_lambda_tiny_decodilo_smoke_discovery(
        discovery,
        LambdaTinyDecodiloSmokeDiscovery(
            discovery_status="found_safe_tiny_smoke_command",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "tiny-smoke"],
            timeout_seconds=30,
        ),
    )
    write_lambda_tiny_decodilo_smoke_policy(
        policy,
        LambdaTinyDecodiloSmokePolicy(
            policy_status="policy_passed",
            one_tiny_decodilo_smoke_command=True,
            bounded_timeout=True,
            bounded_output=True,
        ),
    )
    write_lambda_m073r_tiny_smoke_authorization(
        authorization,
        LambdaM073RTinySmokeAuthorization(
            authorization_status="authorized_for_future_m073r_tiny_decodilo_smoke",
        ),
    )
    write_lambda_m073r_tiny_smoke_runbook_preview(
        preview,
        LambdaM073RTinySmokeRunbookPreview(
            preview_status="ready_for_future_m073r_tiny_smoke_review",
        ),
    )

    report = build_lambda_m072a_report_from_paths(
        smoke_discovery=discovery,
        smoke_policy=policy,
        authorization=authorization,
        runbook_preview=preview,
    )

    assert report.report_passed is True
    assert report.tiny_smoke_command_added is True
    assert report.m073r_authorization_status == (
        "authorized_for_future_m073r_tiny_decodilo_smoke"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
