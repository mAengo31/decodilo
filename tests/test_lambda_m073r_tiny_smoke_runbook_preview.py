from __future__ import annotations

from decodilo.lambda_cloud.m073r_tiny_smoke_authorization import (
    LambdaM073RTinySmokeAuthorization,
    write_lambda_m073r_tiny_smoke_authorization,
)
from decodilo.lambda_cloud.m073r_tiny_smoke_runbook_preview import (
    build_lambda_m073r_tiny_smoke_runbook_preview_from_path,
)


def test_m073r_runbook_preview_blocks_without_command(tmp_path):
    auth_path = tmp_path / "auth.json"
    write_lambda_m073r_tiny_smoke_authorization(
        auth_path,
        LambdaM073RTinySmokeAuthorization(
            authorization_status="not_authorized",
            blockers=["no_safe_tiny_smoke_command_found"],
        ),
    )

    preview = build_lambda_m073r_tiny_smoke_runbook_preview_from_path(
        authorization=auth_path,
    )

    assert preview.preview_status == "blocked_no_safe_tiny_smoke_command"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False


def test_m073r_runbook_preview_ready_for_future_authorized_command(tmp_path):
    auth_path = tmp_path / "auth.json"
    write_lambda_m073r_tiny_smoke_authorization(
        auth_path,
        LambdaM073RTinySmokeAuthorization(
            authorization_status="authorized_for_future_m073r_tiny_decodilo_smoke",
        ),
    )

    preview = build_lambda_m073r_tiny_smoke_runbook_preview_from_path(
        authorization=auth_path,
    )

    assert preview.preview_status == "ready_for_future_m073r_tiny_smoke_review"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
