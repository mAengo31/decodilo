from decodilo.lambda_cloud.response_capture_settings_lock import (
    build_lambda_response_capture_settings_lock,
)


def test_default_response_capture_lock_passes_review_only():
    lock = build_lambda_response_capture_settings_lock()

    assert lock.lock_passed is True
    assert lock.capture_http_status_before_parse is True
    assert lock.body_sample_enabled is False
    assert lock.launch_ready is False
    assert lock.launch_allowed is False


def test_missing_status_before_parse_blocks_lock():
    lock = build_lambda_response_capture_settings_lock(
        capture_http_status_before_parse=False
    )

    assert lock.lock_passed is False
    assert "capture_http_status_before_parse" in lock.blockers


def test_secret_redaction_disabled_blocks_lock():
    lock = build_lambda_response_capture_settings_lock(secret_redaction_enabled=False)

    assert lock.lock_passed is False
    assert "secret_redaction_enabled" in lock.blockers
