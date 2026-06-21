"""Root-cause assessment for repeated Lambda launch response loss."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.launch_endpoint_diagnostics import (
    LambdaLaunchEndpointDiagnosticsReport,
)
from decodilo.lambda_cloud.launch_transport_diagnostics import (
    LambdaLaunchTransportDiagnosticsReport,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report

LambdaLaunchResponseLossCategory = Literal[
    "client_timeout_too_short",
    "endpoint_returns_non_json",
    "endpoint_mapping_wrong",
    "provider_async_behavior",
    "request_sent_but_launch_rejected_without_body",
    "network_transport_issue",
    "unknown",
]
LambdaLaunchResponseLossRootCauseStatus = Literal["unknown", "suspected", "confirmed"]


class LambdaLaunchResponseLossRootCauseReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    repeated_response_loss_detected: bool
    attempts_analyzed: int
    response_loss_count: int
    successful_launch_response_count: int
    likely_categories: list[LambdaLaunchResponseLossCategory] = Field(default_factory=list)
    root_cause_status: LambdaLaunchResponseLossRootCauseStatus = "unknown"
    required_before_next_launch: list[str] = Field(default_factory=list)
    mitigation_accepted: bool = False
    future_launch_blocked: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_flags(self) -> LambdaLaunchResponseLossRootCauseReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("root-cause report cannot enable launch")
        if self.repeated_response_loss_detected and not self.mitigation_accepted:
            if not self.future_launch_blocked:
                raise ValueError("unmitigated repeated response loss must block future launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_lambda_launch_response_loss_root_cause(
    *,
    attempts: list[LambdaM029Report],
    transport_diagnostics: LambdaLaunchTransportDiagnosticsReport | None = None,
    endpoint_diagnostics: LambdaLaunchEndpointDiagnosticsReport | None = None,
    mitigation_accepted: bool = False,
) -> LambdaLaunchResponseLossRootCauseReport:
    response_loss_count = sum(
        int(report.launch_request_sent and not report.launch_response_received)
        for report in attempts
    )
    successful_count = sum(int(report.launch_response_received) for report in attempts)
    repeated = response_loss_count >= 2
    categories = _categories(
        transport_diagnostics=transport_diagnostics,
        endpoint_diagnostics=endpoint_diagnostics,
    )
    status: LambdaLaunchResponseLossRootCauseStatus = (
        "suspected" if categories != ["unknown"] else "unknown"
    )
    if mitigation_accepted and transport_diagnostics and endpoint_diagnostics:
        status = "confirmed" if endpoint_diagnostics.endpoint_diagnostics_passed else "suspected"
    required = [
        "increase timeout or capture raw status safely",
        "record HTTP status code even on parse failure",
        "capture redacted response headers/body metadata",
        "verify endpoint path/method with docs/operator",
        "add no-body/no-training launch payload validation",
        "add dry-run parser fixture from redacted response if available",
    ]
    warnings: list[str] = []
    if response_loss_count == 1:
        warnings.append("single launch response loss observed")
    if repeated:
        warnings.append("two launch response losses observed; future launch hold required")
    return LambdaLaunchResponseLossRootCauseReport(
        repeated_response_loss_detected=repeated,
        attempts_analyzed=len(attempts),
        response_loss_count=response_loss_count,
        successful_launch_response_count=successful_count,
        likely_categories=categories,
        root_cause_status=status,
        required_before_next_launch=[] if mitigation_accepted else required,
        mitigation_accepted=mitigation_accepted,
        future_launch_blocked=bool(repeated and not mitigation_accepted),
        warnings=warnings,
    )


def _categories(
    *,
    transport_diagnostics: LambdaLaunchTransportDiagnosticsReport | None,
    endpoint_diagnostics: LambdaLaunchEndpointDiagnosticsReport | None,
) -> list[LambdaLaunchResponseLossCategory]:
    categories: list[LambdaLaunchResponseLossCategory] = []
    if transport_diagnostics:
        if transport_diagnostics.failure_kind == "timeout":
            categories.append("client_timeout_too_short")
        elif transport_diagnostics.failure_kind == "malformed_response":
            categories.append("endpoint_returns_non_json")
        elif transport_diagnostics.failure_kind in {"http_error", "transport_error"}:
            categories.append("network_transport_issue")
    if endpoint_diagnostics and not endpoint_diagnostics.endpoint_diagnostics_passed:
        categories.append("endpoint_mapping_wrong")
    return categories or ["unknown"]


def write_lambda_launch_response_loss_root_cause(
    path: str | Path,
    report: LambdaLaunchResponseLossRootCauseReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
