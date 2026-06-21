import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.strand_cli_response_shapes import (
    StrandInstanceListResponse,
    parse_strand_error_message,
    parse_strand_launch_instance_id,
    parse_strand_terminate_success,
)


def test_launch_response_parses_data_instance_ids():
    assert parse_strand_launch_instance_id({"data": {"instance_ids": ["i-123"]}}) == "i-123"


def test_missing_instance_ids_fails_clearly():
    with pytest.raises(ValidationError):
        parse_strand_launch_instance_id({"data": {}})


def test_terminate_2xx_empty_body_succeeds():
    assert parse_strand_terminate_success(status_code=204, payload=None) is True


def test_error_message_parsed():
    assert parse_strand_error_message({"error": {"message": "bad request"}}) == "bad request"


def test_unknown_fields_are_preserved():
    response = StrandInstanceListResponse.model_validate(
        {"data": [{"id": "i-123"}], "next": "token"}
    )

    assert response.model_extra["next"] == "token"
