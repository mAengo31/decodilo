"""Acceptance gate for repeated Lambda launch response-loss mitigation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.launch_endpoint_verification import (
    LambdaEndpointVerificationReport,
    load_lambda_endpoint_verification_report,
)
from decodilo.lambda_cloud.response_loss_regression_harness import (
    LambdaResponseLossRegressionReport,
    load_lambda_response_loss_regression_report,
)


class LambdaResponseLossMitigationAcceptanceReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    response_capture_implemented: bool
    status_captured_before_parse: bool
    redacted_headers_content_type_body_size_captured: bool
    timeout_vs_malformed_distinguished: bool
    fake_regression_harness_passed: bool
    endpoint_spec_recorded: bool
    endpoint_spec_status: str
    endpoint_spec_confidence: str
    no_automatic_launch_retry_enforced: bool
    candidate_reconciliation_plan_enforced: bool
    mitigation_accepted: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    future_launch_hold_can_release: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaResponseLossMitigationAcceptanceReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("response-loss mitigation cannot enable launch")
        if self.mitigation_accepted and self.blockers:
            raise ValueError("accepted mitigation cannot have blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def accept_lambda_response_loss_mitigation(
    *,
    endpoint_verification: LambdaEndpointVerificationReport,
    regression_report: LambdaResponseLossRegressionReport,
    response_capture_implemented: bool = True,
    no_automatic_launch_retry_enforced: bool = True,
    candidate_reconciliation_plan_enforced: bool = True,
) -> LambdaResponseLossMitigationAcceptanceReport:
    blockers: list[str] = []
    warnings: list[str] = []
    if not response_capture_implemented:
        blockers.append("http_response_capture_missing")
    status_captured = all(
        result.diagnostic_report.status_captured_before_parse
        for result in regression_report.scenario_results
    )
    if not status_captured:
        blockers.append("status_not_captured_before_parse")
    captures_metadata = all(
        result.diagnostic_report.diagnostics
        and result.diagnostic_report.diagnostics[0].response_capture is not None
        and result.diagnostic_report.diagnostics[0].response_capture.metadata.body_size_bytes
        is not None
        for result in regression_report.scenario_results
        if "timeout" not in result.observed_classification
    )
    if not captures_metadata:
        blockers.append("redacted_response_metadata_incomplete")
    distinguished = _distinguishes_timeout_vs_malformed(regression_report)
    if not distinguished:
        blockers.append("timeout_vs_malformed_not_distinguished")
    if not regression_report.regression_harness_passed:
        blockers.append("response_loss_regression_harness_failed")
    if not endpoint_verification.endpoint_verification_passed:
        blockers.append("endpoint_spec_not_verified")
    if endpoint_verification.confidence not in {"medium", "high"}:
        blockers.append("endpoint_spec_confidence_too_low")
    if not no_automatic_launch_retry_enforced:
        blockers.append("automatic_launch_retry_allowed")
    if not candidate_reconciliation_plan_enforced:
        blockers.append("candidate_reconciliation_plan_missing")
    if endpoint_verification.confidence == "medium":
        warnings.append("endpoint spec is medium confidence; operator reapproval remains required")
    if any("unofficial behavioral evidence" in item for item in endpoint_verification.warnings):
        warnings.append(
            "endpoint spec is based on unofficial CLI behavior; "
            "support confirmation remains distinct"
        )
    accepted = not blockers
    return LambdaResponseLossMitigationAcceptanceReport(
        response_capture_implemented=response_capture_implemented,
        status_captured_before_parse=status_captured,
        redacted_headers_content_type_body_size_captured=captures_metadata,
        timeout_vs_malformed_distinguished=distinguished,
        fake_regression_harness_passed=regression_report.regression_harness_passed,
        endpoint_spec_recorded=bool(endpoint_verification.endpoint_specs),
        endpoint_spec_status="passed"
        if endpoint_verification.endpoint_verification_passed
        else "blocked",
        endpoint_spec_confidence=endpoint_verification.confidence,
        no_automatic_launch_retry_enforced=no_automatic_launch_retry_enforced,
        candidate_reconciliation_plan_enforced=candidate_reconciliation_plan_enforced,
        mitigation_accepted=accepted,
        blockers=blockers,
        warnings=warnings,
        future_launch_hold_can_release=accepted,
    )


def accept_lambda_response_loss_mitigation_from_paths(
    *,
    endpoint_spec: str | Path,
    regression_report: str | Path,
) -> LambdaResponseLossMitigationAcceptanceReport:
    return accept_lambda_response_loss_mitigation(
        endpoint_verification=load_lambda_endpoint_verification_report(endpoint_spec),
        regression_report=load_lambda_response_loss_regression_report(regression_report),
    )


def _distinguishes_timeout_vs_malformed(
    report: LambdaResponseLossRegressionReport,
) -> bool:
    observed = {result.observed_classification for result in report.scenario_results}
    return "timeout" in observed and bool(
        observed & {"success_empty_body", "success_non_json", "schema_validation_failure"}
    )


def load_lambda_response_loss_mitigation_acceptance(
    path: str | Path,
) -> LambdaResponseLossMitigationAcceptanceReport:
    return LambdaResponseLossMitigationAcceptanceReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_response_loss_mitigation_acceptance(
    path: str | Path,
    report: LambdaResponseLossMitigationAcceptanceReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
