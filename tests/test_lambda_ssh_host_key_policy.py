import pytest

from decodilo.lambda_cloud.ssh_host_key_policy import (
    LambdaSSHHostKeyPolicyReport,
    build_lambda_ssh_host_key_policy,
)


def test_ssh_host_key_policy_allows_isolated_accept_new():
    report = build_lambda_ssh_host_key_policy()

    assert report.host_key_policy_status == "policy_defined"
    assert report.isolated_known_hosts_file is True
    assert report.strict_host_key_checking_policy == "accept-new"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_host_key_policy_blocks_strict_checking_no():
    report = build_lambda_ssh_host_key_policy(strict_host_key_checking="no")

    assert report.host_key_policy_status == "blocked"
    assert "strict_host_key_checking_no_forbidden" in report.blockers


def test_ssh_host_key_policy_blocks_global_known_hosts():
    report = build_lambda_ssh_host_key_policy(global_known_hosts_modified=True)

    assert report.host_key_policy_status == "blocked"
    assert "global_known_hosts_must_not_be_modified" in report.blockers


def test_ssh_host_key_policy_rejects_launch_flags():
    with pytest.raises(ValueError):
        LambdaSSHHostKeyPolicyReport.model_validate(
            {
                **build_lambda_ssh_host_key_policy().model_dump(),
                "launch_allowed": True,
            }
        )
