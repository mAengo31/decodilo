from decodilo.lambda_cloud.ssh_identity_policy import build_lambda_ssh_identity_policy


def test_ssh_identity_policy_requires_identities_only():
    report = build_lambda_ssh_identity_policy()

    assert report.identity_policy_status == "policy_defined"
    assert report.identities_only_required is True
    assert report.identity_file_reference_count == 1
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_identity_policy_blocks_multiple_identities():
    report = build_lambda_ssh_identity_policy(identity_file_reference_count=2)

    assert report.identity_policy_status == "blocked"
    assert "exactly_one_identity_file_required" in report.blockers


def test_ssh_identity_policy_blocks_agent_identities():
    report = build_lambda_ssh_identity_policy(agent_identities_allowed=True)

    assert report.identity_policy_status == "blocked"
    assert "agent_identities_forbidden" in report.blockers
