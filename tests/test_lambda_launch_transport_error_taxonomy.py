from decodilo.lambda_cloud.launch_transport_error_taxonomy import (
    classify_lambda_launch_transport_error,
)


def test_transport_error_taxonomy_classifies_http_and_timeout():
    assert (
        classify_lambda_launch_transport_error(
            status_code=404,
            response_classification="http_error_json",
        ).error_type
        == "http_4xx"
    )
    assert (
        classify_lambda_launch_transport_error(
            status_code=503,
            response_classification="http_error_non_json",
        ).error_type
        == "http_5xx"
    )
    assert (
        classify_lambda_launch_transport_error(
            exception_type="TimeoutError",
            response_classification="timeout",
        ).error_type
        == "timeout"
    )


def test_transport_error_taxonomy_classifies_body_failures():
    assert (
        classify_lambda_launch_transport_error(
            status_code=200,
            response_classification="malformed_json",
        ).error_type
        == "malformed_json"
    )
    assert (
        classify_lambda_launch_transport_error(
            status_code=200,
            response_classification="success_non_json",
        ).error_type
        == "non_json_response"
    )
    assert (
        classify_lambda_launch_transport_error(
            status_code=200,
            response_classification="success_empty_body",
        ).error_type
        == "empty_response"
    )
