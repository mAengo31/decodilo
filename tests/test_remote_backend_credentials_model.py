import pytest

from decodilo.storage.remote_backend_credentials_model import (
    CredentialHandlingPolicy,
    CredentialRequirement,
    SecretRef,
    audit_credential_policy,
)


def test_secret_ref_accepts_symbolic_metadata() -> None:
    ref = SecretRef(
        name="remote-backend-syncer-key",
        provider="future-provider",
        purpose="syncer artifact access",
        rotation_policy="90d",
    )
    report = audit_credential_policy(
        CredentialHandlingPolicy(
            credential_requirements=[
                CredentialRequirement(
                    requirement_id="syncer",
                    secret_ref=ref,
                    required_for_operations=["manifest:write"],
                )
            ]
        )
    )

    assert report.passed is True
    assert report.symbolic_secret_refs[0]["name"] == "remote-backend-syncer-key"
    assert "secret_value" not in report.to_json()


def test_secret_ref_rejects_raw_secret_fields_and_values() -> None:
    with pytest.raises(ValueError):
        SecretRef.model_validate(
            {
                "name": "remote-key",
                "provider": "manual",
                "purpose": "test",
                "secret_value": "abc123",
            }
        )
    with pytest.raises(ValueError):
        SecretRef(
            name="AKIA1234567890123456",
            provider="manual",
            purpose="test",
        )


def test_credential_policy_rejects_environment_reads() -> None:
    report = audit_credential_policy(
        CredentialHandlingPolicy(read_environment_variables=True)
    )

    assert report.passed is False
    assert "environment variables" in report.errors[0]
