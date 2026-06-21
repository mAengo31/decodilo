from decodilo.lambda_cloud.crash_safe_transport_diagnostics import (
    validate_lambda_crash_safe_transport_diagnostics,
)
from decodilo.lambda_cloud.http_response_capture import capture_lambda_http_response
from decodilo.lambda_cloud.mutation_failure_report_writer import (
    build_lambda_mutation_failure_report,
)
from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnostics,
    build_lambda_mutation_transport_diagnostic_report,
)
from decodilo.lambda_cloud.transport_error_persistence import (
    build_lambda_transport_error_persistence_record,
)


def _failure_report(classification_body: bytes = b'{"error":"bad"}'):
    capture = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/instance-operations/launch",
        endpoint_path="/instance-operations/launch",
        mutation_operation_name="launch_one_instance",
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=classification_body,
        exception_type="LambdaRealMutationTransportError",
    )
    diagnostic = LambdaMutationTransportDiagnostics(
        operation="launch_one_instance",
        stages=["request_sent", "status_received", "exception_raised"],
        response_capture=capture,
    )
    record = build_lambda_transport_error_persistence_record(
        operation="launch_one_instance",
        request_sent=True,
        exception=RuntimeError("M029 real Lambda HTTP error"),
        elapsed_seconds=0.2,
        diagnostics=[diagnostic],
    )
    return (
        build_lambda_mutation_failure_report(
            transport_error=record,
            diagnostics_persisted=True,
        ),
        build_lambda_mutation_transport_diagnostic_report([diagnostic]),
    )


def test_crash_safe_diagnostics_accepts_persisted_error():
    failure, diagnostics = _failure_report()

    report = validate_lambda_crash_safe_transport_diagnostics(
        failure_report=failure,
        diagnostic_report=diagnostics,
    )

    assert report.diagnostics_hardening_accepted is True
    assert report.response_capture_persisted is True
    assert report.no_auto_retry is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_missing_diagnostics_blocks_acceptance():
    failure, _diagnostics = _failure_report()
    failure = failure.model_copy(update={"diagnostics_persisted": False})

    report = validate_lambda_crash_safe_transport_diagnostics(failure_report=failure)

    assert report.diagnostics_hardening_accepted is False
    assert "transport_diagnostics_not_persisted" in report.blockers
