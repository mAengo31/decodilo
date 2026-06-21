import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.strand_cli_request_shapes import (
    build_strand_launch_payload,
    build_strand_terminate_payload,
    validate_strand_launch_payload,
    validate_strand_terminate_payload,
)


def test_launch_request_matches_strand_shape():
    payload = build_strand_launch_payload(
        region_name="us-west-1",
        instance_type_name="gpu_1x_h100_pcie",
        ssh_key_name="existing-key",
    )

    assert payload == {
        "region_name": "us-west-1",
        "instance_type_name": "gpu_1x_h100_pcie",
        "ssh_key_names": ["existing-key"],
        "quantity": 1,
    }
    assert validate_strand_launch_payload(payload).quantity == 1


def test_wrong_launch_field_names_fail():
    with pytest.raises(ValidationError):
        validate_strand_launch_payload(
            {
                "region": "us-west-1",
                "gpu_type": "gpu_1x_h100_pcie",
                "ssh_key_names": ["existing-key"],
                "quantity": 1,
            }
        )


def test_missing_ssh_key_names_fail():
    with pytest.raises(ValidationError):
        validate_strand_launch_payload(
            {
                "region_name": "us-west-1",
                "instance_type_name": "gpu_1x_h100_pcie",
                "quantity": 1,
            }
        )


def test_quantity_must_be_one():
    with pytest.raises(ValidationError):
        validate_strand_launch_payload(
            {
                "region_name": "us-west-1",
                "instance_type_name": "gpu_1x_h100_pcie",
                "ssh_key_names": ["existing-key"],
                "quantity": 2,
            }
        )


def test_terminate_request_matches_strand_shape():
    payload = build_strand_terminate_payload("i-123")

    assert payload == {"instance_ids": ["i-123"]}
    assert validate_strand_terminate_payload(payload).instance_ids == ["i-123"]
