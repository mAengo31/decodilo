from decodilo.lambda_cloud.http_response_capture import capture_lambda_http_response
from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnostics,
)
from decodilo.lambda_cloud.transport_error_persistence import (
    build_lambda_transport_error_persistence_record,
)


def test_http_error_before_parse_persists_redacted_metadata():
    capture = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/instance-operations/launch",
        endpoint_path="/instance-operations/launch",
        mutation_operation_name="launch_one_instance",
        status_code=400,
        headers={"Content-Type": "application/json", "Authorization": "Bearer secret"},
        body=b'{"error":{"message":"bad request"}}',
        exception_type="LambdaRealMutationTransportError",
        exception_message="M029 real Lambda HTTP error",
        billable_action_performed=True,
    )
    diagnostic = LambdaMutationTransportDiagnostics(
        operation="launch_one_instance",
        stages=["request_sent", "status_received", "exception_raised"],
        response_capture=capture,
        real_lambda_api_used=True,
    )

    record = build_lambda_transport_error_persistence_record(
        operation="launch_one_instance",
        request_sent=True,
        exception=RuntimeError("M029 real Lambda HTTP error"),
        elapsed_seconds=0.25,
        diagnostics=[diagnostic],
    )

    assert record.status_code == 400
    assert record.provider_error_message_redacted == "bad request"
    assert record.response_classification == "http_error_json"
    assert record.taxonomy.error_type == "http_4xx"
    assert record.no_auto_retry is True
    assert record.secret_scan_passed is True


def test_timeout_persists_without_status():
    capture = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/instance-operations/launch",
        endpoint_path="/instance-operations/launch",
        mutation_operation_name="launch_one_instance",
        exception=TimeoutError("timed out"),
    )
    diagnostic = LambdaMutationTransportDiagnostics(
        operation="launch_one_instance",
        stages=["request_sent", "timeout_detected", "exception_raised"],
        response_capture=capture,
    )

    record = build_lambda_transport_error_persistence_record(
        operation="launch_one_instance",
        request_sent=True,
        exception=TimeoutError("timed out"),
        elapsed_seconds=30.0,
        diagnostics=[diagnostic],
    )

    assert record.status_code is None
    assert record.response_classification == "timeout"
    assert record.taxonomy.error_type == "timeout"
