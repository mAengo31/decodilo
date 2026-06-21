import json
from pathlib import Path

import pytest

from decodilo.lambda_cloud.credential_model import LambdaAPIKeyRef, LambdaCredentialError


def test_lambda_fixtures_contain_no_raw_api_keys() -> None:
    payload = "\n".join(path.read_text(encoding="utf-8") for path in Path(
        "tests/fixtures/lambda_cloud"
    ).glob("*.json"))

    assert "api_key" not in payload.lower()
    assert "private_key" not in payload.lower()
    assert "lambda_" not in payload.lower()


def test_lambda_secret_like_report_json_rejected() -> None:
    with pytest.raises(LambdaCredentialError):
        LambdaAPIKeyRef.model_validate(
            {
                "key_name": "future",
                "purpose": "bad",
                "required_scope": "read_only",
                "token": "lambda_123456789012345678901234",
            }
        )

    assert "lambda_123456789012345678901234" in json.dumps(
        {"example": "lambda_123456789012345678901234"}
    )
