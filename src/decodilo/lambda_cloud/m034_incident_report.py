"""M034C launch failure incident report and status evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.launch_failure_journal_recovery import (
    LambdaLaunchFailureJournalRecoveryReport,
    recover_lambda_launch_failure_from_journal,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report, load_lambda_m029_report
from decodilo.lambda_cloud.m034_discovery_diff import (
    LambdaM034DiscoveryDiffReport,
    load_lambda_m034_discovery_diff,
)
from decodilo.lambda_cloud.m034_manual_console_confirmation import (
    LambdaM034ManualConsoleConfirmationReport,
    load_lambda_m034_manual_console_confirmation,
)
from decodilo.lambda_cloud.m034_owned_instance_reconciliation import (
    LambdaM034OwnedInstanceReconciliationReport,
    reconcile_m034_owned_instance,
)
from decodilo.lambda_cloud.transport_error_persistence import (
    LambdaTransportErrorPersistenceRecord,
    load_lambda_transport_error_persistence_record,
)

LambdaM034IncidentStatus = Literal[
    "open",
    "closed_no_instance_visible",
    "closed_manual_termination_verified",
    "unresolved_requires_manual_review",
]


class LambdaM034IncidentReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    incident_id: str = "lambda-m034c-crash-safe-response-loss"
    source_m034_report_or_journal: str
    launch_request_sent: bool
    launch_response_received: bool
    transport_error_type: str | None = None
    transport_error_persisted: bool = False
    response_capture_persisted: bool = False
    owned_instance_id_present: bool
    termination_request_sent: bool
    termination_verified: bool
    manual_review_required: bool
    estimated_spend: float | None = None
    elapsed_seconds: float | None = None
    post_discovery_summary: dict[str, int | bool | None] = Field(default_factory=dict)
    discovery_diff: LambdaM034DiscoveryDiffReport
    owned_instance_reconciliation: LambdaM034OwnedInstanceReconciliationReport
    console_confirmation: LambdaM034ManualConsoleConfirmationReport
    journal_recovery: LambdaLaunchFailureJournalRecoveryReport | None = None
    incident_status: LambdaM034IncidentStatus
    crash_safe_diagnostics_required: bool = True
    future_launch_blocked: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_flags(self) -> LambdaM034IncidentReport:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M034 incident report cannot enable launch")
        if not self.future_launch_blocked:
            raise ValueError("M034 incident keeps future launch held until hardening passes")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m034_incident_report(
    *,
    source_m034_report_or_journal: str | Path,
    discovery_diff: LambdaM034DiscoveryDiffReport,
    console_confirmation: LambdaM034ManualConsoleConfirmationReport,
    m034_report: LambdaM029Report | None = None,
    journal_recovery: LambdaLaunchFailureJournalRecoveryReport | None = None,
    transport_error: LambdaTransportErrorPersistenceRecord | None = None,
    owned_instance_reconciliation: LambdaM034OwnedInstanceReconciliationReport | None = None,
) -> LambdaM034IncidentReport:
    reconciliation = owned_instance_reconciliation or reconcile_m034_owned_instance(
        discovery_diff=discovery_diff
    )
    state = _state_from_report_or_recovery(m034_report=m034_report, recovery=journal_recovery)
    status = _incident_status(
        state=state,
        discovery_diff=discovery_diff,
        console=console_confirmation,
        reconciliation=reconciliation,
    )
    warnings = ["M034C is the third ambiguous/lost launch response event"]
    if not state["report_present"]:
        warnings.append("M034C report.json was missing; incident state recovered from journal")
    if status == "closed_no_instance_visible":
        warnings.append(
            "closed based on read-only zero-instance evidence plus console confirmation"
        )
    elif status == "unresolved_requires_manual_review":
        warnings.append("manual provider console review is still required")
    if transport_error is None:
        warnings.append("transport error diagnostics were not persisted for this attempt")
    return LambdaM034IncidentReport(
        source_m034_report_or_journal=str(source_m034_report_or_journal),
        launch_request_sent=bool(state["launch_request_sent"]),
        launch_response_received=bool(state["launch_response_received"]),
        transport_error_type=(
            None if transport_error is None else transport_error.taxonomy.error_type
        ),
        transport_error_persisted=transport_error is not None,
        response_capture_persisted=bool(
            transport_error is not None
            and transport_error.response_classification != "unknown"
        ),
        owned_instance_id_present=bool(state["owned_instance_id_present"]),
        termination_request_sent=bool(state["termination_request_sent"]),
        termination_verified=bool(state["termination_verified"]),
        manual_review_required=bool(state["manual_review_required"]),
        estimated_spend=state["estimated_spend"],
        elapsed_seconds=state["elapsed_seconds"],
        post_discovery_summary={
            "post_instance_count": discovery_diff.post_instance_count,
            "closeout_instance_count": discovery_diff.closeout_instance_count,
            "billable_state_count": len(discovery_diff.billable_state_instances),
            "possible_owned_candidate_count": len(discovery_diff.possible_owned_candidates),
        },
        discovery_diff=discovery_diff,
        owned_instance_reconciliation=reconciliation,
        console_confirmation=console_confirmation,
        journal_recovery=journal_recovery,
        incident_status=status,
        future_launch_blocked=True,
        warnings=warnings,
        errors=[] if transport_error is None else transport_error.errors,
    )


def build_lambda_m034_incident_report_from_paths(
    *,
    discovery_diff: str | Path,
    console_confirmation: str | Path,
    m034_report: str | Path | None = None,
    journal: str | Path | None = None,
    transport_error: str | Path | None = None,
) -> LambdaM034IncidentReport:
    diff = load_lambda_m034_discovery_diff(discovery_diff)
    loaded_report = (
        load_lambda_m029_report(m034_report)
        if m034_report is not None and Path(m034_report).exists()
        else None
    )
    recovery = None
    source: str | Path
    if loaded_report is None:
        if journal is None:
            raise ValueError("M034 incident report requires report.json or journal")
        recovery = recover_lambda_launch_failure_from_journal(
            journal,
            report_path=m034_report,
        )
        source = journal
    else:
        source = m034_report  # type: ignore[assignment]
    loaded_error = (
        load_lambda_transport_error_persistence_record(transport_error)
        if transport_error is not None and Path(transport_error).exists()
        else None
    )
    return build_lambda_m034_incident_report(
        source_m034_report_or_journal=source,
        m034_report=loaded_report,
        journal_recovery=recovery,
        discovery_diff=diff,
        console_confirmation=load_lambda_m034_manual_console_confirmation(
            console_confirmation
        ),
        transport_error=loaded_error,
        owned_instance_reconciliation=reconcile_m034_owned_instance(
            discovery_diff=diff,
            journal_path=journal,
        ),
    )


def _state_from_report_or_recovery(
    *,
    m034_report: LambdaM029Report | None,
    recovery: LambdaLaunchFailureJournalRecoveryReport | None,
) -> dict[str, bool | float | None]:
    if m034_report is not None:
        return {
            "report_present": True,
            "launch_request_sent": m034_report.launch_request_sent,
            "launch_response_received": m034_report.launch_response_received,
            "owned_instance_id_present": bool(m034_report.owned_instance_id_redacted),
            "termination_request_sent": m034_report.termination_request_sent,
            "termination_verified": m034_report.termination_verified,
            "manual_review_required": m034_report.manual_review_required,
            "estimated_spend": m034_report.estimated_spend,
            "elapsed_seconds": m034_report.elapsed_seconds,
        }
    if recovery is None:
        return {
            "report_present": False,
            "launch_request_sent": False,
            "launch_response_received": False,
            "owned_instance_id_present": False,
            "termination_request_sent": False,
            "termination_verified": False,
            "manual_review_required": True,
            "estimated_spend": None,
            "elapsed_seconds": None,
        }
    return {
        "report_present": False,
        "launch_request_sent": recovery.launch_request_sent,
        "launch_response_received": recovery.response_received,
        "owned_instance_id_present": bool(recovery.owned_instance_id),
        "termination_request_sent": recovery.termination_request_sent,
        "termination_verified": recovery.termination_verified,
        "manual_review_required": recovery.manual_review_required,
        "estimated_spend": None,
        "elapsed_seconds": None,
    }


def _incident_status(
    *,
    state: dict[str, bool | float | None],
    discovery_diff: LambdaM034DiscoveryDiffReport,
    console: LambdaM034ManualConsoleConfirmationReport,
    reconciliation: LambdaM034OwnedInstanceReconciliationReport,
) -> LambdaM034IncidentStatus:
    if (
        not state["owned_instance_id_present"]
        and not state["termination_request_sent"]
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
        and bool(state["termination_verified"])
    ):
        return "closed_manual_termination_verified"
    if bool(state["manual_review_required"]) or reconciliation.manual_review_required:
        return "unresolved_requires_manual_review"
    return "open"


def load_lambda_m034_incident_report(path: str | Path) -> LambdaM034IncidentReport:
    return LambdaM034IncidentReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m034_incident_report(
    path: str | Path,
    report: LambdaM034IncidentReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
