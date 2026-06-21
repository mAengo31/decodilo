from decodilo.lambda_cloud.http_response_capture import (
    LambdaHTTPResponseCapturePolicy,
    capture_lambda_http_response,
)


def test_json_success_classified_and_status_captured_before_parse():
    report = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/instance-operations/launch",
        endpoint_path="/instance-operations/launch",
        mutation_operation_name="launch_one_instance",
        status_code=200,
        headers={"Content-Type": "application/json", "Authorization": "Bearer secret"},
        body=b'{"data":{"instance_ids":["fake-i-1"]}}',
    )

    assert report.classification == "success_json"
    assert report.status_captured_before_parse is True
    assert report.metadata.headers_redacted["Authorization"] == "<redacted-secret>"
    assert report.metadata.secret_scan_passed is True


def test_empty_non_json_http_error_timeout_and_malformed_classifications():
    empty = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/launch",
        endpoint_path="/launch",
        mutation_operation_name="launch_one_instance",
        status_code=200,
        body=b"",
    )
    non_json = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/launch",
        endpoint_path="/launch",
        mutation_operation_name="launch_one_instance",
        status_code=200,
        headers={"Content-Type": "text/plain"},
        body=b"accepted",
    )
    http_error = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/launch",
        endpoint_path="/launch",
        mutation_operation_name="launch_one_instance",
        status_code=500,
        headers={"Content-Type": "text/plain"},
        body=b"server error",
    )
    timeout = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/launch",
        endpoint_path="/launch",
        mutation_operation_name="launch_one_instance",
        exception_type="TimeoutError",
        exception_message="timed out",
    )
    malformed = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/launch",
        endpoint_path="/launch",
        mutation_operation_name="launch_one_instance",
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=b"{not json",
    )

    assert empty.classification == "success_empty_body"
    assert non_json.classification == "success_non_json"
    assert http_error.classification == "http_error_non_json"
    assert timeout.classification == "timeout"
    assert malformed.classification == "malformed_json"


def test_4xx_json_error_message_is_persisted_redacted_without_body_sample():
    report = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/instance-operations/launch",
        endpoint_path="/instance-operations/launch",
        mutation_operation_name="launch_one_instance",
        status_code=400,
        headers={
            "Content-Type": "application/json",
            "Set-Cookie": "__cf_bm=secret-cookie-value",
        },
        body=b'{"error":{"message":"invalid request api_key=abcdefghi"}}',
    )

    assert report.classification == "http_error_json"
    assert (
        report.metadata.provider_error_message_redacted
        == "invalid request <redacted-secret>"
    )
    assert report.metadata.response_body_sample_redacted is None
    assert report.metadata.headers_redacted["Set-Cookie"] == "<redacted-secret>"
    assert report.metadata.secret_scan_passed is True


def test_body_sample_is_limited_and_redacted():
    report = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/launch",
        endpoint_path="/launch",
        mutation_operation_name="launch_one_instance",
        status_code=200,
        headers={"Content-Type": "text/plain"},
        body="Bearer very-secret-token " + ("x" * 100),
        policy=LambdaHTTPResponseCapturePolicy(
            capture_body_sample=True,
            max_body_sample_bytes=32,
        ),
    )

    assert report.metadata.response_body_sample_redacted is not None
    assert "very-secret-token" not in report.metadata.response_body_sample_redacted
    assert len(report.metadata.response_body_sample_redacted) <= 64
    assert report.launch_ready is False
    assert report.launch_allowed is False
