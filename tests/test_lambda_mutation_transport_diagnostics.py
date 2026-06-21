from decodilo.lambda_cloud.http_response_capture import capture_lambda_http_response
from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnostics,
    build_lambda_mutation_transport_diagnostic_report,
)


def test_diagnostics_distinguish_timeout_from_malformed_response():
    timeout = LambdaMutationTransportDiagnostics(
        operation="launch_one_instance",
        stages=["request_sent", "timeout_detected", "exception_raised"],
        response_capture=capture_lambda_http_response(
            method="POST",
            endpoint_path_template="/launch",
            endpoint_path="/launch",
            mutation_operation_name="launch_one_instance",
            exception_type="TimeoutError",
        ),
    )
    malformed = LambdaMutationTransportDiagnostics(
        operation="launch_one_instance",
        stages=["request_sent", "status_received", "parse_started", "parse_failed"],
        response_capture=capture_lambda_http_response(
            method="POST",
            endpoint_path_template="/launch",
            endpoint_path="/launch",
            mutation_operation_name="launch_one_instance",
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=b"{bad",
        ),
    )

    report = build_lambda_mutation_transport_diagnostic_report([timeout, malformed])

    assert report.timeout_detected is True
    assert report.malformed_response_detected is True
    assert report.status_captured_before_parse is True
    assert report.parse_failure_detected is True
    assert report.no_secret_leakage is True


def test_diagnostic_report_serializes_stably():
    diagnostic = LambdaMutationTransportDiagnostics(
        operation="terminate_owned_instance",
        stages=["request_sent", "status_received", "parse_started", "parse_completed"],
        response_capture=capture_lambda_http_response(
            method="DELETE",
            endpoint_path_template="/terminate",
            endpoint_path="/terminate",
            mutation_operation_name="terminate_owned_instance",
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=b'{"data":{"terminated_instances":[]}}',
        ),
    )

    report = build_lambda_mutation_transport_diagnostic_report([diagnostic])

    assert report.to_json() == report.to_json()
    assert "Authorization" not in report.to_json()
