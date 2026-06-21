import pytest
from lambda_m036_helpers import support_payload, support_response

from decodilo.lambda_cloud.support_confirmation_response import (
    ingest_lambda_support_confirmation_response,
)


def test_complete_support_confirmation_response_validates_and_serializes():
    response = support_response()

    assert response.confidence == "high"
    assert response.secret_scan_passed is True
    assert "launch_method" in response.answer_map()
    assert response.launch_ready is False
    assert response.launch_allowed is False


def test_missing_launch_endpoint_answer_is_ingested_but_incomplete_for_validator():
    response = support_response(missing=("launch_path_template",))

    assert "launch_path_template" not in response.answer_map()


def test_secret_like_answer_is_rejected():
    payload = support_payload()
    payload["answers"]["launch_method"] = "Authorization: Bearer secret-token"

    with pytest.raises(ValueError, match="secret-like"):
        ingest_lambda_support_confirmation_response(payload)

