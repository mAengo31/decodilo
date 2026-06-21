import json
import subprocess
import sys

from lambda_m034d_helpers import write_m034c_sent_journal

from decodilo.lambda_cloud.http_response_capture import capture_lambda_http_response
from decodilo.lambda_cloud.mutation_failure_report_writer import (
    write_lambda_mutation_failure_artifacts,
)
from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnostics,
    build_lambda_mutation_transport_diagnostic_report,
    write_lambda_mutation_transport_diagnostic_report,
)
from decodilo.lambda_cloud.transport_error_persistence import (
    build_lambda_transport_error_persistence_record,
)


def test_m034_incident_cli_closes_no_visible_case(tmp_path):
    console = tmp_path / "console.json"
    diff = tmp_path / "diff.json"
    incident = tmp_path / "incident.json"
    closeout = tmp_path / "closeout.json"
    journal = write_m034c_sent_journal(tmp_path)
    pre = tmp_path / "pre.json"
    post = tmp_path / "post.json"
    pre.write_text('{"instances":[]}\n', encoding="utf-8")
    post.write_text('{"instances":[]}\n', encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "m034",
            "incident",
            "console-confirmation",
            "--lambda-console-checked",
            "--no-instances-visible",
            "--no-pending-instances-visible",
            "--no-alert-instances-visible",
            "--no-owned-instance-found",
            "--out",
            str(console),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "m034",
            "incident",
            "discovery-diff",
            "--pre-discovery",
            str(pre),
            "--post-discovery",
            str(post),
            "--out",
            str(diff),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "m034",
            "incident",
            "report",
            "--journal",
            str(journal),
            "--discovery-diff",
            str(diff),
            "--console-confirmation",
            str(console),
            "--out",
            str(incident),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "m034",
            "incident",
            "closeout",
            "--incident-report",
            str(incident),
            "--out",
            str(closeout),
        ],
        check=True,
    )

    payload = json.loads(closeout.read_text(encoding="utf-8"))
    assert payload["closeout_succeeded"] is True
    assert payload["future_launch_hold_active"] is True


def test_m034_validate_crash_safe_cli(tmp_path):
    capture = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/instance-operations/launch",
        endpoint_path="/instance-operations/launch",
        mutation_operation_name="launch_one_instance",
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=b'{"error":"bad"}',
    )
    diagnostic = LambdaMutationTransportDiagnostics(
        operation="launch_one_instance",
        stages=["request_sent", "status_received", "exception_raised"],
        response_capture=capture,
    )
    diagnostic_report = build_lambda_mutation_transport_diagnostic_report([diagnostic])
    diagnostic_path = tmp_path / "diagnostics.json"
    write_lambda_mutation_transport_diagnostic_report(diagnostic_path, diagnostic_report)
    record = build_lambda_transport_error_persistence_record(
        operation="launch_one_instance",
        request_sent=True,
        exception=RuntimeError("M029 real Lambda HTTP error"),
        elapsed_seconds=0.1,
        diagnostics=[diagnostic],
    )
    failure = write_lambda_mutation_failure_artifacts(
        workdir=tmp_path,
        transport_error=record,
        diagnostics_report=diagnostic_report,
    )
    assert failure.diagnostics_persisted is True
    out = tmp_path / "crash-safe.json"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "m034",
            "diagnostics",
            "validate-crash-safe",
            "--failure-report",
            str(tmp_path / "mutation-failure-report.json"),
            "--diagnostic-report",
            str(diagnostic_path),
            "--out",
            str(out),
        ],
        check=True,
    )

    assert json.loads(out.read_text(encoding="utf-8"))[
        "diagnostics_hardening_accepted"
    ]
