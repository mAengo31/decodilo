from decodilo.lambda_cloud.remote_access_policy import build_lambda_remote_access_policy


def test_remote_access_policy_denies_ssh_by_default():
    report = build_lambda_remote_access_policy()

    assert report.default_access_mode == "provider_metadata_only"
    assert report.ssh_allowed_without_operator_approval is False
    assert report.ssh_key_attachment_implies_ssh_approval is False
    assert report.arbitrary_shell_allowed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
