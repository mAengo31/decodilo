from decodilo.lambda_cloud.http_response_capture import capture_lambda_http_response
from decodilo.lambda_cloud.mutation_failure_report_writer import (
    write_lambda_mutation_failure_artifacts,
)
from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnostics,
    build_lambda_mutation_transport_diagnostic_report,
)
from decodilo.lambda_cloud.transport_error_persistence import (
    build_lambda_transport_error_persistence_record,
)


def test_failure_report_writer_persists_artifacts(tmp_path):
    capture = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/instance-operations/launch",
        endpoint_path="/instance-operations/launch",
        mutation_operation_name="launch_one_instance",
        status_code=500,
        headers={"Content-Type": "text/plain"},
        body=b"provider error",
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
        elapsed_seconds=0.1,
        diagnostics=[diagnostic],
    )

    report = write_lambda_mutation_failure_artifacts(
        workdir=tmp_path,
        transport_error=record,
        diagnostics_report=build_lambda_mutation_transport_diagnostic_report([diagnostic]),
    )

    assert report.diagnostics_persisted is True
    assert (tmp_path / "transport-error.json").exists()
    assert (tmp_path / "transport-diagnostics.json").exists()
    assert (tmp_path / "mutation-failure-report.json").exists()


def test_failure_report_writer_fallback_path(tmp_path, monkeypatch):
    capture = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/instance-operations/launch",
        endpoint_path="/instance-operations/launch",
        mutation_operation_name="launch_one_instance",
        exception=TimeoutError("timed out"),
    )
    diagnostic = LambdaMutationTransportDiagnostics(
        operation="launch_one_instance",
        stages=["request_sent", "timeout_detected"],
        response_capture=capture,
    )
    record = build_lambda_transport_error_persistence_record(
        operation="launch_one_instance",
        request_sent=True,
        exception=TimeoutError("timed out"),
        elapsed_seconds=30,
        diagnostics=[diagnostic],
    )

    def fail_write(*args, **kwargs):  # noqa: ARG001
        raise OSError("disk write failed")

    monkeypatch.setattr(
        "decodilo.lambda_cloud.mutation_failure_report_writer."
        "write_lambda_transport_error_persistence_record",
        fail_write,
    )
    report = write_lambda_mutation_failure_artifacts(
        workdir=tmp_path,
        transport_error=record,
    )

    assert report.emergency_fallback_written is True
    assert (tmp_path / "mutation-failure-fallback.json").exists()
