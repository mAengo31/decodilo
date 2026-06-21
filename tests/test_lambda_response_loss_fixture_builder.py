from decodilo.lambda_cloud.response_loss_fixture_builder import (
    build_lambda_response_loss_diagnostic_fixture,
)


def test_fixture_builder_classifies_empty_body_and_timeout():
    empty = build_lambda_response_loss_diagnostic_fixture("launch_status_200_empty_body")
    timeout = build_lambda_response_loss_diagnostic_fixture(
        "terminate_timeout_before_status"
    )

    assert empty.response_capture.classification == "success_empty_body"
    assert timeout.response_capture.classification == "timeout"
    assert empty.no_real_lambda_call is True
    assert timeout.launch_allowed is False


def test_fixture_builder_redacts_headers_and_serializes():
    fixture = build_lambda_response_loss_diagnostic_fixture("launch_status_5xx_non_json")

    payload = fixture.to_json()

    assert fixture.response_capture.classification == "http_error_non_json"
    assert "Bearer" not in payload
    assert payload == fixture.to_json()
