from decodilo.lambda_cloud.ssh_private_key_file_policy import (
    build_lambda_ssh_private_key_file_policy,
)


def test_ssh_private_key_file_policy_accepts_0600():
    report = build_lambda_ssh_private_key_file_policy(checked_mode=0o600)

    assert report.private_key_file_policy_status == "policy_defined"
    assert report.permission_policy == "0600_or_stricter"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_private_key_file_policy_blocks_0644():
    report = build_lambda_ssh_private_key_file_policy(checked_mode=0o644)

    assert report.private_key_file_policy_status == "blocked"
    assert "private_key_permissions_too_open" in report.blockers


def test_ssh_private_key_file_policy_blocks_raw_private_key_material():
    report = build_lambda_ssh_private_key_file_policy(
        serialized_value="-----BEGIN OPENSSH PRIVATE KEY-----\nredacted\n"
    )

    assert report.private_key_file_policy_status == "blocked"
    assert "raw_private_key_material_serialized" in report.blockers


def test_ssh_private_key_file_policy_blocks_public_key_material():
    report = build_lambda_ssh_private_key_file_policy(
        serialized_value="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFake"
    )

    assert report.private_key_file_policy_status == "blocked"
    assert "raw_public_key_material_serialized" in report.blockers
