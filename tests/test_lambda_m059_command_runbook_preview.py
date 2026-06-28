from __future__ import annotations

from decodilo.lambda_cloud.m059_command_runbook_preview import (
    build_lambda_m059_command_runbook_preview_from_path,
)
from decodilo.lambda_cloud.m059_remote_command_authorization import (
    LambdaM059RemoteCommandAuthorization,
    write_lambda_m059_remote_command_authorization,
)


def test_m059_runbook_preview_is_non_executable(tmp_path):
    auth_path = tmp_path / "auth.json"
    write_lambda_m059_remote_command_authorization(
        auth_path,
        LambdaM059RemoteCommandAuthorization(
            authorization_status="authorized_for_future_m059_identity_command_review",
            selected_future_command_set=["hostname"],
        ),
    )

    preview = build_lambda_m059_command_runbook_preview_from_path(
        authorization=auth_path,
    )

    assert preview.preview_status == "ready_for_future_m059_identity_command_review"
    assert preview.executable is False
    assert preview.selected_future_command_set == ["hostname"]
    assert preview.package_install_allowed is False
    assert preview.training_allowed is False
    assert preview.launch_ready is False
    assert preview.launch_allowed is False
