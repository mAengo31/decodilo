"""M029 ambiguous-launch incident report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m029_discovery_diff import (
    LambdaM029DiscoveryDiffReport,
    load_lambda_m029_discovery_diff,
)
from decodilo.lambda_cloud.m029_manual_console_confirmation import (
    LambdaM029ManualConsoleConfirmationReport,
    load_lambda_m029_manual_console_confirmation,
)
from decodilo.lambda_cloud.m029_owned_instance_reconciliation import (
    LambdaM029OwnedInstanceReconciliationReport,
    reconcile_m029_owned_instance,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report, load_lambda_m029_report

LambdaM029IncidentStatus = Literal[
    "open",
    "closed_no_instance_visible",
    "closed_manual_termination_verified",
    "unresolved_requires_manual_review",
]


class LambdaM029IncidentReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    incident_id: str = "lambda-m029c-ambiguous-launch"
    source_m029_report: str
    launch_request_sent: bool
    launch_response_received: bool
    owned_instance_id_present: bool
    termination_request_sent: bool
    termination_verified: bool
    manual_review_required: bool
    estimated_spend: float
    elapsed_seconds: float
    post_discovery_summary: dict[str, int | bool | None] = Field(default_factory=dict)
    discovery_diff: LambdaM029DiscoveryDiffReport
    owned_instance_reconciliation: LambdaM029OwnedInstanceReconciliationReport
    console_confirmation: LambdaM029ManualConsoleConfirmationReport
    incident_status: LambdaM029IncidentStatus
    second_launch_blocked: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_flags(self) -> LambdaM029IncidentReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M029 incident report cannot enable launch")
        if self.incident_status.startswith("closed_") and self.second_launch_blocked:
            raise ValueError("closed incident should clear only the incident blocker")
        if not self.incident_status.startswith("closed_") and not self.second_launch_blocked:
            raise ValueError("open or unresolved incident must block second launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m029_incident_report(
    *,
    source_m029_report: str | Path,
    m029_report: LambdaM029Report,
    discovery_diff: LambdaM029DiscoveryDiffReport,
    console_confirmation: LambdaM029ManualConsoleConfirmationReport,
    owned_instance_reconciliation: LambdaM029OwnedInstanceReconciliationReport | None = None,
) -> LambdaM029IncidentReport:
    reconciliation = owned_instance_reconciliation or reconcile_m029_owned_instance(
        discovery_diff=discovery_diff
    )
    status = _incident_status(
        report=m029_report,
        discovery_diff=discovery_diff,
        console=console_confirmation,
        reconciliation=reconciliation,
    )
    warnings: list[str] = []
    if status == "unresolved_requires_manual_review":
        warnings.append("manual provider console review is still required")
    elif status == "closed_no_instance_visible":
        warnings.append(
            "closed based on read-only zero-instance evidence plus console confirmation"
        )
    return LambdaM029IncidentReport(
        source_m029_report=str(source_m029_report),
        launch_request_sent=m029_report.launch_request_sent,
        launch_response_received=m029_report.launch_response_received,
        owned_instance_id_present=bool(m029_report.owned_instance_id_redacted),
        termination_request_sent=m029_report.termination_request_sent,
        termination_verified=m029_report.termination_verified,
        manual_review_required=m029_report.manual_review_required,
        estimated_spend=m029_report.estimated_spend,
        elapsed_seconds=m029_report.elapsed_seconds,
        post_discovery_summary={
            "post_instance_count": discovery_diff.post_instance_count,
            "billable_state_count": len(discovery_diff.billable_state_instances),
            "possible_owned_candidate_count": len(discovery_diff.possible_owned_candidates),
        },
        discovery_diff=discovery_diff,
        owned_instance_reconciliation=reconciliation,
        console_confirmation=console_confirmation,
        incident_status=status,
        second_launch_blocked=not status.startswith("closed_"),
        warnings=warnings,
    )


def build_lambda_m029_incident_report_from_paths(
    *,
    m029_report: str | Path,
    discovery_diff: str | Path,
    console_confirmation: str | Path,
) -> LambdaM029IncidentReport:
    diff = load_lambda_m029_discovery_diff(discovery_diff)
    return build_lambda_m029_incident_report(
        source_m029_report=m029_report,
        m029_report=load_lambda_m029_report(m029_report),
        discovery_diff=diff,
        console_confirmation=load_lambda_m029_manual_console_confirmation(
            console_confirmation
        ),
        owned_instance_reconciliation=reconcile_m029_owned_instance(discovery_diff=diff),
    )


def _incident_status(
    *,
    report: LambdaM029Report,
    discovery_diff: LambdaM029DiscoveryDiffReport,
    console: LambdaM029ManualConsoleConfirmationReport,
    reconciliation: LambdaM029OwnedInstanceReconciliationReport,
) -> LambdaM029IncidentStatus:
    if (
        not report.owned_instance_id_redacted
        and not report.termination_request_sent
        and not discovery_diff.billable_state_instances
        and discovery_diff.confidence
        in {"high_no_instance_created", "likely_no_instance_created"}
        and console.confirmation_status == "confirmed_no_visible_instances"
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


def load_lambda_m029_incident_report(path: str | Path) -> LambdaM029IncidentReport:
    return LambdaM029IncidentReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m029_incident_report(
    path: str | Path,
    report: LambdaM029IncidentReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
