"""Mutation transport diagnostic event model for Lambda launch/terminate paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.http_response_capture import LambdaHTTPResponseCapture

LambdaMutationDiagnosticStage = Literal[
    "before_request_constructed",
    "request_constructed",
    "request_sent",
    "status_received",
    "parse_started",
    "parse_completed",
    "parse_failed",
    "exception_raised",
    "timeout_detected",
]


class LambdaMutationTransportDiagnostics(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation: str
    stages: list[LambdaMutationDiagnosticStage] = Field(default_factory=list)
    response_capture: LambdaHTTPResponseCapture | None = None
    no_secret_leakage: bool = True
    real_lambda_api_used: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_flags(self) -> LambdaMutationTransportDiagnostics:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("mutation diagnostics cannot enable launch")
        if not self.no_secret_leakage:
            raise ValueError("mutation diagnostics must not leak secrets")
        return self


class LambdaMutationTransportDiagnosticReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    diagnostics: list[LambdaMutationTransportDiagnostics] = Field(default_factory=list)
    timeout_detected: bool = False
    malformed_response_detected: bool = False
    status_captured_before_parse: bool = False
    parse_failure_detected: bool = False
    no_secret_leakage: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_flags(self) -> LambdaMutationTransportDiagnosticReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("mutation diagnostic report cannot enable launch")
        if not self.no_secret_leakage:
            raise ValueError("mutation diagnostic report must not leak secrets")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_mutation_transport_diagnostic_report(
    diagnostics: list[LambdaMutationTransportDiagnostics],
) -> LambdaMutationTransportDiagnosticReport:
    timeout = any(
        "timeout_detected" in item.stages
        or (item.response_capture and item.response_capture.classification == "timeout")
        for item in diagnostics
    )
    malformed = any(
        item.response_capture
        and item.response_capture.classification
        in {
            "malformed_json",
            "schema_validation_failure",
            "success_non_json",
            "success_empty_body",
            "http_error_non_json",
        }
        for item in diagnostics
    )
    status_before_parse = any(
        bool(item.response_capture and item.response_capture.status_captured_before_parse)
        for item in diagnostics
    )
    parse_failed = any(
        "parse_failed" in item.stages
        or bool(
            item.response_capture
            and item.response_capture.classification
            in {"malformed_json", "schema_validation_failure"}
        )
        for item in diagnostics
    )
    return LambdaMutationTransportDiagnosticReport(
        diagnostics=diagnostics,
        timeout_detected=timeout,
        malformed_response_detected=malformed,
        status_captured_before_parse=status_before_parse,
        parse_failure_detected=parse_failed,
        no_secret_leakage=all(item.no_secret_leakage for item in diagnostics),
    )


def write_lambda_mutation_transport_diagnostic_report(
    path: str | Path,
    report: LambdaMutationTransportDiagnosticReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
