from decodilo.lambda_cloud.live_discovery_redaction import (
    LambdaLiveDiscoveryRedactionPolicy,
    audit_lambda_redaction,
    redact_lambda_payload,
    scan_lambda_secret_leaks,
)


def test_lambda_live_discovery_redaction_removes_secret_strings() -> None:
    payload = {
        "Authorization": "Bearer lambda_12345678901234567890",
        "instance_id": "i-public-secret-test",
    }
    redacted = redact_lambda_payload(
        payload,
        policy=LambdaLiveDiscoveryRedactionPolicy(mode="public_summary"),
    )

    assert "Bearer" not in str(redacted)
    assert "lambda_12345678901234567890" not in str(redacted)
    assert redacted["instance_id"] != payload["instance_id"]


def test_lambda_live_discovery_local_private_keeps_ids_but_not_secrets() -> None:
    payload = {
        "instance_id": "i-private-kept",
        "api_key": "lambda_12345678901234567890",
    }
    redacted = redact_lambda_payload(
        payload,
        policy=LambdaLiveDiscoveryRedactionPolicy(mode="local_private_report"),
    )

    assert redacted["instance_id"] == "i-private-kept"
    assert "lambda_12345678901234567890" not in str(redacted)
    assert audit_lambda_redaction(redacted).passed


def test_lambda_secret_scanner_detects_generated_report_leaks() -> None:
    clean_report = {
        "secret_source": "env_file",
        "env_file_basename": ".env",
        "env_key": "LAMBDA_API_KEY",
        "secret_loaded": True,
        "redacted": True,
    }
    dirty_report = {"headers": {"Authorization": "Bearer lambda_12345678901234567890"}}

    assert scan_lambda_secret_leaks(clean_report) == []
    assert scan_lambda_secret_leaks(dirty_report)
