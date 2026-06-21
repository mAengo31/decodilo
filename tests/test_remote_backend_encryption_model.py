import pytest

from decodilo.storage.remote_backend_credentials_model import SecretRef
from decodilo.storage.remote_backend_encryption_model import (
    EncryptionPolicy,
    evaluate_encryption_policy,
)


def test_encryption_policy_passes_with_provider_managed_model() -> None:
    report = evaluate_encryption_policy(EncryptionPolicy())

    assert report.passed is True


def test_missing_server_side_encryption_configuration_blocks() -> None:
    report = evaluate_encryption_policy(
        EncryptionPolicy(key_management_model="not_configured")
    )

    assert report.passed is False
    assert any("server-side encryption" in error for error in report.errors)


def test_raw_key_reference_rejected() -> None:
    with pytest.raises(ValueError):
        EncryptionPolicy(
            key_management_model="customer_managed",
            key_ref=SecretRef(
                name="-----BEGIN PRIVATE KEY-----abcdef",
                provider="manual",
                purpose="bad",
            ),
        )
