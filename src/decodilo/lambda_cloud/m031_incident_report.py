"""M031 repeated launch-response-loss incident report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m029_report import LambdaM029Report, load_lambda_m029_report
from decodilo.lambda_cloud.m031_discovery_diff import (
    LambdaM031DiscoveryDiffReport,
    load_lambda_m031_discovery_diff,
)
from decodilo.lambda_cloud.m031_manual_console_confirmation import (
    LambdaM031ManualConsoleConfirmationReport,
    load_lambda_m031_manual_console_confirmation,
)
from decodilo.lambda_cloud.m031_owned_instance_reconciliation import (
    LambdaM031OwnedInstanceReconciliationReport,
    reconcile_m031_owned_instance,
)

LambdaM031IncidentStatus = Literal[
    "open",
    "closed_no_instance_visible",
    "closed_manual_termination_verified",
    "unresolved_requires_manual_review",
]


class LambdaM031IncidentReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    incident_id: str = "lambda-m031-repeated-response-loss"
    source_m031_report: str
    launch_request_sent: bool
    launch_response_received: bool
    owned_instance_id_present: bool
    termination_request_sent: bool
    termination_verified: bool
    manual_review_required: bool
    estimated_spend: float
    elapsed_seconds: float
    post_discovery_summary: dict[str, int | bool | None] = Field(default_factory=dict)
    discovery_diff: LambdaM031DiscoveryDiffReport
    owned_instance_reconciliation: LambdaM031OwnedInstanceReconciliationReport
    console_confirmation: LambdaM031ManualConsoleConfirmationReport
    incident_status: LambdaM031IncidentStatus
    future_launch_blocked: bool = True
    repeated_response_loss_detected: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_flags(self) -> LambdaM031IncidentReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M031 incident report cannot enable launch")
        if self.incident_status.startswith("closed_") and self.future_launch_blocked:
            raise ValueError("closed M031 incident should clear only the incident blocker")
        if not self.incident_status.startswith("closed_") and not self.future_launch_blocked:
            raise ValueError("open or unresolved M031 incident must block future launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m031_incident_report(
    *,
    source_m031_report: str | Path,
    m031_report: LambdaM029Report,
    discovery_diff: LambdaM031DiscoveryDiffReport,
    console_confirmation: LambdaM031ManualConsoleConfirmationReport,
    owned_instance_reconciliation: LambdaM031OwnedInstanceReconciliationReport | None = None,
) -> LambdaM031IncidentReport:
    reconciliation = owned_instance_reconciliation or reconcile_m031_owned_instance(
        discovery_diff=discovery_diff
    )
    status = _incident_status(
        report=m031_report,
        discovery_diff=discovery_diff,
        console=console_confirmation,
        reconciliation=reconciliation,
    )
    warnings: list[str] = ["M031 is the second launch-response-loss event"]
    if status == "unresolved_requires_manual_review":
        warnings.append("manual provider console review is still required")
    elif status == "closed_no_instance_visible":
        warnings.append(
            "closed based on read-only zero-instance evidence plus console confirmation"
        )
    return LambdaM031IncidentReport(
        source_m031_report=str(source_m031_report),
        launch_request_sent=m031_report.launch_request_sent,
        launch_response_received=m031_report.launch_response_received,
        owned_instance_id_present=bool(m031_report.owned_instance_id_redacted),
        termination_request_sent=m031_report.termination_request_sent,
        termination_verified=m031_report.termination_verified,
        manual_review_required=m031_report.manual_review_required,
        estimated_spend=m031_report.estimated_spend,
        elapsed_seconds=m031_report.elapsed_seconds,
        post_discovery_summary={
            "post_instance_count": discovery_diff.post_instance_count,
            "closeout_instance_count": discovery_diff.closeout_instance_count,
            "billable_state_count": len(discovery_diff.billable_state_instances),
            "possible_owned_candidate_count": len(discovery_diff.possible_owned_candidates),
        },
        discovery_diff=discovery_diff,
        owned_instance_reconciliation=reconciliation,
        console_confirmation=console_confirmation,
        incident_status=status,
        future_launch_blocked=not status.startswith("closed_"),
        warnings=warnings,
    )


def build_lambda_m031_incident_report_from_paths(
    *,
    m031_report: str | Path,
    discovery_diff: str | Path,
    console_confirmation: str | Path,
) -> LambdaM031IncidentReport:
    diff = load_lambda_m031_discovery_diff(discovery_diff)
    return build_lambda_m031_incident_report(
        source_m031_report=m031_report,
        m031_report=load_lambda_m029_report(m031_report),
        discovery_diff=diff,
        console_confirmation=load_lambda_m031_manual_console_confirmation(
            console_confirmation
        ),
        owned_instance_reconciliation=reconcile_m031_owned_instance(discovery_diff=diff),
    )


def _incident_status(
    *,
    report: LambdaM029Report,
    discovery_diff: LambdaM031DiscoveryDiffReport,
    console: LambdaM031ManualConsoleConfirmationReport,
    reconciliation: LambdaM031OwnedInstanceReconciliationReport,
) -> LambdaM031IncidentStatus:
    if (
        not report.owned_instance_id_redacted
        and not report.termination_request_sent
        and not discovery_diff.billable_state_instances
        and discovery_diff.confidence
        in {"high_no_instance_created", "likely_no_instance_created"}
        and console.confirmation_status == "confirmed_no_visible_instances"
        and console.no_owned_instance_found
        and not reconciliation.owned_instance_id_found
    ):
        return "closed_no_instance_visible"
    if (
        console.confirmation_status == "confirmed_manual_termination_performed"
        and report.termination_verified
    ):
        return "closed_manual_termination_verified"
    if report.manual_review_required or reconciliation.manual_review_required:
        return "unresolved_requires_manual_review"
    return "open"


def load_lambda_m031_incident_report(path: str | Path) -> LambdaM031IncidentReport:
    return LambdaM031IncidentReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m031_incident_report(
    path: str | Path,
    report: LambdaM031IncidentReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
