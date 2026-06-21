"""Crash-safe writers for Lambda mutation failure artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnosticReport,
)
from decodilo.lambda_cloud.transport_error_persistence import (
    LambdaTransportErrorPersistenceRecord,
    write_lambda_transport_error_persistence_record,
)


class LambdaMutationFailureReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    failure_report_id: str = "lambda-mutation-failure-report"
    transport_error: LambdaTransportErrorPersistenceRecord
    diagnostics_persisted: bool
    emergency_fallback_written: bool = False
    manual_review_required: bool = True
    no_auto_retry: bool = True
    secret_scan_passed: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaMutationFailureReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("mutation failure report cannot enable launch")
        if not self.no_auto_retry:
            raise ValueError("mutation failure report must preserve no-auto-retry")
        if not self.secret_scan_passed:
            raise ValueError("mutation failure report must not leak secrets")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_mutation_failure_report(
    *,
    transport_error: LambdaTransportErrorPersistenceRecord,
    diagnostics_persisted: bool,
    emergency_fallback_written: bool = False,
) -> LambdaMutationFailureReport:
    return LambdaMutationFailureReport(
        transport_error=transport_error,
        diagnostics_persisted=diagnostics_persisted,
        emergency_fallback_written=emergency_fallback_written,
        secret_scan_passed=transport_error.secret_scan_passed,
        warnings=[
            *transport_error.warnings,
            "normal mutation run failed; crash-safe failure artifact persisted",
        ],
        errors=transport_error.errors,
    )


def write_lambda_mutation_failure_artifacts(
    *,
    workdir: str | Path,
    transport_error: LambdaTransportErrorPersistenceRecord,
    diagnostics_report: LambdaMutationTransportDiagnosticReport | None = None,
) -> LambdaMutationFailureReport:
    target_dir = Path(workdir)
    target_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_persisted = False
    fallback_written = False
    try:
        write_lambda_transport_error_persistence_record(
            target_dir / "transport-error.json",
            transport_error,
        )
        if diagnostics_report is not None:
            (target_dir / "transport-diagnostics.json").write_text(
                diagnostics_report.to_json(),
                encoding="utf-8",
            )
            diagnostics_persisted = True
        report = build_lambda_mutation_failure_report(
            transport_error=transport_error,
            diagnostics_persisted=diagnostics_persisted,
        )
        (target_dir / "mutation-failure-report.json").write_text(
            report.to_json(),
            encoding="utf-8",
        )
        return report
    except Exception as exc:  # noqa: BLE001 - emergency fallback path
        fallback_written = True
        fallback = {
            "report_schema_version": 1,
            "failure_report_id": "lambda-mutation-failure-fallback",
            "operation": transport_error.operation,
            "request_sent": transport_error.request_sent,
            "exception_type": transport_error.exception_type,
            "writer_exception_type": type(exc).__name__,
            "manual_review_required": True,
            "no_auto_retry": True,
            "launch_ready": False,
            "launch_allowed": False,
        }
        (target_dir / "mutation-failure-fallback.json").write_text(
            json.dumps(fallback, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return build_lambda_mutation_failure_report(
            transport_error=transport_error,
            diagnostics_persisted=diagnostics_persisted,
            emergency_fallback_written=fallback_written,
        )


def load_lambda_mutation_failure_report(path: str | Path) -> LambdaMutationFailureReport:
    return LambdaMutationFailureReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
