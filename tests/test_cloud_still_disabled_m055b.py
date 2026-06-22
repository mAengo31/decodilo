from decodilo.lambda_cloud.ssh_failure_stderr_capture import (
    build_lambda_ssh_stderr_capture_policy,
)
from decodilo.lambda_cloud.ssh_host_key_policy import build_lambda_ssh_host_key_policy
from decodilo.lambda_cloud.ssh_identity_policy import build_lambda_ssh_identity_policy
from decodilo.lambda_cloud.ssh_private_key_file_policy import (
    build_lambda_ssh_private_key_file_policy,
)
from decodilo.lambda_cloud.ssh_username_policy import build_lambda_ssh_username_policy


def test_m055b_artifacts_keep_cloud_launch_disabled():
    reports = [
        build_lambda_ssh_username_policy(),
        build_lambda_ssh_host_key_policy(),
        build_lambda_ssh_identity_policy(),
        build_lambda_ssh_private_key_file_policy(),
        build_lambda_ssh_stderr_capture_policy(),
    ]

    for report in reports:
        assert report.launch_ready is False
        assert report.launch_allowed is False
        assert report.billable_action_performed is False
