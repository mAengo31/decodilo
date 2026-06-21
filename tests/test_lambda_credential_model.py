import json

import pytest

from decodilo.lambda_cloud.credential_model import (
    LambdaAPIKeyRef,
    LambdaCredentialError,
    LambdaCredentialPolicy,
    audit_lambda_credentials,
)


def test_symbolic_lambda_api_key_ref_is_accepted() -> None:
    ref = LambdaAPIKeyRef(
        key_name="lambda-readonly-prod",
        owner="platform",
        purpose="future read-only discovery",
        required_scope="read_only",
    )
    report = audit_lambda_credentials(LambdaCredentialPolicy(api_key_refs=[ref]))

    assert report.passed
    assert report.symbolic_ref_count == 1
    assert "lambda-readonly-prod" in json.dumps(ref.model_dump(mode="json"))


def test_raw_lambda_api_key_like_values_are_rejected() -> None:
    with pytest.raises(LambdaCredentialError):
        LambdaAPIKeyRef(
            key_name="bad",
            purpose="bad",
            required_scope="read_only",
            api_key="lambda_12345678901234567890",  # type: ignore[call-arg]
        )


def test_credential_policy_rejects_env_reads() -> None:
    with pytest.raises(LambdaCredentialError):
        LambdaCredentialPolicy(env_reads_allowed=True)
