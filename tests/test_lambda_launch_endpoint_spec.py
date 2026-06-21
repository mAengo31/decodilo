import pytest

from decodilo.lambda_cloud.launch_endpoint_spec import build_lambda_endpoint_spec


def test_high_confidence_launch_endpoint_spec_validates():
    spec = build_lambda_endpoint_spec(
        operation="launch_one_instance",
        method="POST",
        path_template="/instance-operations/launch",
        source_url="https://docs.lambda.ai/public-cloud/cloud-api/",
        confidence="high",
    )

    assert spec.method == "POST"
    assert spec.verified_for_real_mutation is True
    assert spec.launch_allowed is False


def test_missing_method_or_path_blocks():
    with pytest.raises(ValueError):
        build_lambda_endpoint_spec(
            operation="launch_one_instance",
            method="",
            path_template="/instance-operations/launch",
        )
    with pytest.raises(ValueError):
        build_lambda_endpoint_spec(
            operation="terminate_owned_instance",
            method="DELETE",
            path_template="",
        )


def test_unknown_operation_rejected():
    with pytest.raises(ValueError):
        build_lambda_endpoint_spec(
            operation="restart_instance",
            method="POST",
            path_template="/instance-operations/restart",
        )
