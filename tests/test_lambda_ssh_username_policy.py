import pytest

from decodilo.lambda_cloud.ssh_username_policy import (
    LambdaSSHUsernamePolicyReport,
    build_lambda_ssh_username_policy,
)


def test_ssh_username_policy_defaults_to_ubuntu():
    report = build_lambda_ssh_username_policy()

    assert report.username_policy_status == "policy_defined"
    assert report.selected_username == "ubuntu"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_username_policy_blocks_missing_username():
    report = build_lambda_ssh_username_policy(username="")

    assert report.username_policy_status == "blocked"
    assert "ssh_username_missing" in report.blockers


def test_ssh_username_policy_blocks_root_without_override():
    report = build_lambda_ssh_username_policy(username="root")

    assert report.username_policy_status == "blocked"
    assert "root_username_requires_operator_override" in report.blockers


def test_ssh_username_policy_rejects_launch_flags():
    with pytest.raises(ValueError):
        LambdaSSHUsernamePolicyReport.model_validate(
            {
                **build_lambda_ssh_username_policy().model_dump(),
                "launch_ready": True,
            }
        )
