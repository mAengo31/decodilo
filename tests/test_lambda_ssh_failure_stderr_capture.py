from decodilo.lambda_cloud.ssh_failure_stderr_capture import (
    build_lambda_ssh_stderr_capture_policy,
    redact_ssh_stderr,
)


def test_ssh_stderr_capture_policy_is_offline_and_bounded():
    report = build_lambda_ssh_stderr_capture_policy()

    assert report.capture_policy_status == "policy_defined"
    assert report.max_stderr_bytes == 8192
    assert report.max_lines == 80
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_stderr_redacts_key_path_but_keeps_publickey_error():
    report = redact_ssh_stderr(
        "Permission denied (publickey). Identity file /tmp/key not accessible.",
        private_key_path="/tmp/key",
    )

    assert "Permission denied (publickey)" in report.stderr_redacted
    assert "/tmp/key" not in report.stderr_redacted
    assert "<redacted-private-key-reference>" in report.stderr_redacted
    assert report.secret_scan_passed is True


def test_ssh_stderr_redacts_host_and_truncates():
    report = redact_ssh_stderr("line\n" * 100, host="203.0.113.10")

    assert report.stderr_truncated is True
    assert report.secret_scan_passed is True


def test_ssh_stderr_redacts_public_key_material():
    report = redact_ssh_stderr("debug ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFake")

    assert "ssh-ed25519" not in report.stderr_redacted
    assert report.secret_scan_passed is True
