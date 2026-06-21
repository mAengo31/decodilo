"""Acceptance check for crash-safe Lambda mutation diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.mutation_failure_report_writer import (
    LambdaMutationFailureReport,
    load_lambda_mutation_failure_report,
)
from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnosticReport,
)


class LambdaCrashSafeTransportDiagnosticsReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    diagnostics_hardening_accepted: bool
    transport_error_persisted: bool
    response_capture_persisted: bool
    status_captured_before_parse: bool
    timeout_distinguished: bool
    malformed_or_non_json_distinguished: bool
    no_auto_retry: bool
    secret_scan_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaCrashSafeTransportDiagnosticsReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("crash-safe diagnostics report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def validate_lambda_crash_safe_transport_diagnostics(
    *,
    failure_report: LambdaMutationFailureReport,
    diagnostic_report: LambdaMutationTransportDiagnosticReport | None = None,
) -> LambdaCrashSafeTransportDiagnosticsReport:
    transport = failure_report.transport_error
    classifications = [
        item.response_capture.classification
        for item in (diagnostic_report.diagnostics if diagnostic_report else [])
        if item.response_capture is not None
    ]
    timeout_distinguished = (
        transport.response_classification == "timeout"
        or (diagnostic_report.timeout_detected if diagnostic_report else False)
    )
    malformed_distinguished = bool(
        transport.response_classification
        in {
            "malformed_json",
            "success_non_json",
            "success_empty_body",
            "http_error_non_json",
            "schema_validation_failure",
        }
        or any(
            item
            in {
                "malformed_json",
                "success_non_json",
                "success_empty_body",
                "http_error_non_json",
                "schema_validation_failure",
            }
            for item in classifications
        )
    )
    blockers: list[str] = []
    if not failure_report.diagnostics_persisted:
        blockers.append("transport_diagnostics_not_persisted")
    if not transport.request_sent:
        blockers.append("request_attempt_not_recorded")
    if transport.response_classification == "unknown":
        blockers.append("response_classification_missing")
    if not transport.no_auto_retry:
        blockers.append("automatic_retry_not_forbidden")
    if not transport.secret_scan_passed:
        blockers.append("secret_scan_failed")
    accepted = not blockers
    return LambdaCrashSafeTransportDiagnosticsReport(
        diagnostics_hardening_accepted=accepted,
        transport_error_persisted=True,
        response_capture_persisted=transport.response_classification != "unknown",
        status_captured_before_parse=(
            diagnostic_report.status_captured_before_parse if diagnostic_report else True
        ),
        timeout_distinguished=timeout_distinguished,
        malformed_or_non_json_distinguished=malformed_distinguished,
        no_auto_retry=transport.no_auto_retry,
        secret_scan_passed=transport.secret_scan_passed,
        blockers=blockers,
        warnings=[
            "diagnostics hardening release is for future review only; it does not launch"
        ],
    )


def validate_lambda_crash_safe_transport_diagnostics_from_paths(
    *,
    failure_report: str | Path,
    diagnostic_report: str | Path | None = None,
) -> LambdaCrashSafeTransportDiagnosticsReport:
    diag = None
    if diagnostic_report is not None and Path(diagnostic_report).exists():
        diag = LambdaMutationTransportDiagnosticReport.model_validate_json(
            Path(diagnostic_report).read_text(encoding="utf-8")
        )
    return validate_lambda_crash_safe_transport_diagnostics(
        failure_report=load_lambda_mutation_failure_report(failure_report),
        diagnostic_report=diag,
    )


def write_lambda_crash_safe_transport_diagnostics(
    path: str | Path,
    report: LambdaCrashSafeTransportDiagnosticsReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_lambda_crash_safe_transport_diagnostics(
    path: str | Path,
) -> LambdaCrashSafeTransportDiagnosticsReport:
    return LambdaCrashSafeTransportDiagnosticsReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
