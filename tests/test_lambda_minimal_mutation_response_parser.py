import pytest

from decodilo.lambda_cloud.minimal_mutation_response_parser import (
    parse_minimal_mutation_response,
)


def test_fake_launch_response_parses_with_metadata():
    result = parse_minimal_mutation_response(
        {
            "operation": "launch_one_instance",
            "instance_id": "fake-i-abc",
            "lifecycle_state": "running",
            "unknown": "kept",
        }
    )

    assert result.instance_id == "fake-i-abc"
    assert result.metadata["unknown"] == "kept"


def test_fake_strand_launch_response_shape_parses():
    result = parse_minimal_mutation_response({"data": {"instance_ids": ["fake-i-strand"]}})

    assert result.instance_id == "fake-i-strand"
    assert result.metadata["strand_response_shape"] is True


def test_fake_terminate_response_parses():
    result = parse_minimal_mutation_response(
        {
            "operation": "terminate_owned_instance",
            "instance_id": "fake-i-abc",
            "lifecycle_state": "terminated",
            "termination_verified": True,
        }
    )

    assert result.lifecycle_state == "terminated"
    assert result.termination_verified is True


def test_real_lambda_or_billable_response_rejected():
    with pytest.raises(ValueError):
        parse_minimal_mutation_response(
            {
                "operation": "launch_one_instance",
                "instance_id": "fake-i-abc",
                "real_lambda_api_used": True,
            }
        )
    with pytest.raises(ValueError):
        parse_minimal_mutation_response(
            {
                "operation": "launch_one_instance",
                "instance_id": "fake-i-abc",
                "billable_action_performed": True,
            }
        )


def test_non_fake_id_rejected():
    with pytest.raises(ValueError):
        parse_minimal_mutation_response(
            {
                "operation": "launch_one_instance",
                "instance_id": "live-instance-id",
            }
        )
