import pytest

from decodilo.storage.remote_backend_credentials_model import (
    CredentialHandlingPolicy,
    SecretRef,
    audit_credential_policy,
)
from decodilo.storage.remote_backend_readiness import (
    RemoteBackendReadinessStatus,
    evaluate_remote_backend_readiness,
)


def test_secret_like_values_are_rejected_and_not_reported() -> None:
    with pytest.raises(ValueError):
        SecretRef(
            name="remote=super-secret-value",
            provider="manual",
            purpose="bad",
        )

    report = audit_credential_policy(CredentialHandlingPolicy())
    payload = report.to_json()
    assert "super-secret-value" not in payload
    assert "access_key" not in payload
    assert "private_key" not in payload


def test_readiness_raw_secret_detection_blocks_without_leaking_value() -> None:
    report = evaluate_remote_backend_readiness(
        scenario_id="secret-test",
        source_scaling_report_ref="scaling.json",
        requirement_ref="requirements.json",
        validation_report_ref="validation.json",
        conformance_report_ref=None,
        conformance_report=None,
        security_report=None,
        evidence_package=None,
        raw_secret_detected=True,
    )

    assert report.readiness_status == RemoteBackendReadinessStatus.evidence_missing
    assert "no_raw_secrets_present" in report.blockers
    assert "secret-test" in report.to_json()
    assert "super-secret-value" not in report.to_json()
