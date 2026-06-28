from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_authorization import (
    LambdaM075RRuntimeProtocolSmokeAuthorization,
    write_lambda_m075r_runtime_protocol_smoke_authorization,
)
from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_runbook_preview import (
    build_lambda_m075r_runtime_protocol_smoke_runbook_preview_from_path,
)


def test_m075r_runbook_preview_blocks_without_safe_runtime_command(tmp_path):
    auth_path = tmp_path / "auth.json"
    write_lambda_m075r_runtime_protocol_smoke_authorization(
        auth_path,
        LambdaM075RRuntimeProtocolSmokeAuthorization(
            authorization_status="not_authorized",
            blockers=["no_safe_runtime_protocol_smoke_command_found"],
        ),
    )

    preview = build_lambda_m075r_runtime_protocol_smoke_runbook_preview_from_path(
        authorization=auth_path,
    )

    assert preview.preview_status == "blocked_no_safe_runtime_protocol_smoke_command"
    assert preview.executable is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False


def test_m075r_runbook_preview_ready_for_future_authorized_command(tmp_path):
    auth_path = tmp_path / "auth.json"
    write_lambda_m075r_runtime_protocol_smoke_authorization(
        auth_path,
        LambdaM075RRuntimeProtocolSmokeAuthorization(
            authorization_status="authorized_for_future_m075r_runtime_protocol_smoke",
        ),
    )

    preview = build_lambda_m075r_runtime_protocol_smoke_runbook_preview_from_path(
        authorization=auth_path,
    )

    assert preview.preview_status == "ready_for_future_m075r_runtime_protocol_smoke_review"
    assert preview.executable is False
    assert "run exactly one bounded synthetic runtime/protocol smoke command" in (
        preview.future_requirements
    )
