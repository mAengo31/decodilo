from decodilo.lambda_cloud.ssh_retry_command_preview import (
    build_lambda_ssh_retry_command_preview_from_path,
)
from decodilo.lambda_cloud.ssh_retry_future_authorization import (
    LambdaSSHM056AuthorizationReport,
    write_lambda_ssh_retry_future_authorization,
)


def test_m056_retry_command_preview_is_non_executable(tmp_path):
    auth = tmp_path / "auth.json"
    write_lambda_ssh_retry_future_authorization(
        auth,
        LambdaSSHM056AuthorizationReport(
            authorization_status=(
                "authorized_for_future_m056_live_candidate_ssh_retry_review"
            ),
            selected_candidate="gpu_1x_a10",
            selected_region="us-east-1",
            selected_candidate_source="live_readonly_instance_types",
            future_m056_review_authorized=True,
        ),
    )

    report = build_lambda_ssh_retry_command_preview_from_path(auth)

    assert report.preview_status == "ready_for_future_m056_live_candidate_ssh_retry_review"
    assert report.executable is False
    assert "--ssh-stderr-capture-policy" in report.command_preview
    assert report.no_remote_command is True
    assert report.launch_allowed is False
