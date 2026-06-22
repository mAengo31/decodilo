from decodilo.lambda_cloud.ssh_failure_classifier import classify_ssh_failure


def test_ssh_failure_classifier_permission_denied_publickey():
    report = classify_ssh_failure(
        exit_code=255,
        stderr_redacted="Permission denied (publickey).",
        tcp_readiness_succeeded=True,
    )

    assert report.classification == "permission_denied_publickey"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_failure_classifier_host_key_verification_failed():
    report = classify_ssh_failure(
        exit_code=255,
        stderr_redacted="Host key verification failed.",
    )

    assert report.classification == "host_key_verification_failed"


def test_ssh_failure_classifier_private_key_permissions():
    report = classify_ssh_failure(
        exit_code=255,
        stderr_redacted="WARNING: UNPROTECTED PRIVATE KEY FILE!",
    )

    assert report.classification == "private_key_permissions_too_open"


def test_ssh_failure_classifier_no_stderr_exit_255_unknown():
    report = classify_ssh_failure(exit_code=255, stderr_redacted="")

    assert report.classification == "unknown_exit_255"
