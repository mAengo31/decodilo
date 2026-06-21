"""Close out Lambda launch attempts rejected for unavailable capacity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report, load_lambda_m029_report
from decodilo.lambda_cloud.real_launch_spend_audit import (
    LambdaM029SpendAuditReport,
)
from decodilo.lambda_cloud.transport_error_persistence import (
    LambdaTransportErrorPersistenceRecord,
    load_lambda_transport_error_persistence_record,
)

LambdaCapacityErrorCloseoutStatus = Literal[
    "closed_capacity_unavailable_no_instance_created",
    "unresolved",
]


class LambdaCapacityErrorCloseoutReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    launch_request_sent: bool
    status_code: int | None = None
    provider_error_message_redacted: str | None = None
    classification: str | None = None
    selected_shape: str | None = None
    selected_region: str | None = None
    owned_instance_id_present: bool
    termination_required: bool
    termination_attempted: bool
    final_instance_count: int
    final_unmanaged_count: int
    capacity_error_confirmed: bool
    closeout_status: LambdaCapacityErrorCloseoutStatus
    closeout_succeeded: bool
    future_launch_blocked_for_same_shape: bool
    future_availability_first_required: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCapacityErrorCloseoutReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("capacity error closeout cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaCapacityErrorCloseout = LambdaCapacityErrorCloseoutReport


def build_lambda_capacity_error_closeout(
    *,
    m039_report: LambdaM029Report,
    transport_error: LambdaTransportErrorPersistenceRecord | None,
    post_discovery: LambdaLiveDiscoveryReport,
    spend_audit: LambdaM029SpendAuditReport | None = None,
) -> LambdaCapacityErrorCloseoutReport:
    status_code = (
        m039_report.launch_response_http_status
        if m039_report.launch_response_http_status is not None
        else (None if transport_error is None else transport_error.status_code)
    )
    provider_message = (
        m039_report.launch_response_error_message_redacted
        or (None if transport_error is None else transport_error.provider_error_message_redacted)
    )
    classification = (
        m039_report.launch_response_classification
        or (None if transport_error is None else transport_error.response_classification)
    )
    owned_instance_present = bool(m039_report.owned_instance_id_redacted)
    final_instance_count = len(post_discovery.instances)
    final_unmanaged_count = len(post_discovery.unmanaged_instances)
    blockers: list[str] = []
    if not m039_report.launch_request_sent:
        blockers.append("launch_request_not_sent")
    if status_code != 400:
        blockers.append("status_code_not_400_capacity_rejection")
    if not _is_capacity_message(provider_message):
        blockers.append("capacity_error_message_missing_or_unrecognized")
    if classification != "http_error_json":
        blockers.append("launch_response_not_http_error_json")
    if owned_instance_present:
        blockers.append("owned_instance_id_present")
    if final_instance_count != 0 or final_unmanaged_count != 0:
        blockers.append("post_discovery_found_visible_or_unmanaged_instances")
    if spend_audit is not None and spend_audit.budget_exceeded:
        blockers.append("spend_audit_budget_exceeded")
    capacity_confirmed = not {
        "status_code_not_400_capacity_rejection",
        "capacity_error_message_missing_or_unrecognized",
        "launch_response_not_http_error_json",
    }.intersection(blockers)
    closeout_succeeded = not blockers
    return LambdaCapacityErrorCloseoutReport(
        launch_request_sent=m039_report.launch_request_sent,
        status_code=status_code,
        provider_error_message_redacted=provider_message,
        classification=classification,
        selected_shape=m039_report.selected_shape,
        selected_region=m039_report.selected_region,
        owned_instance_id_present=owned_instance_present,
        termination_required=owned_instance_present,
        termination_attempted=m039_report.termination_request_sent,
        final_instance_count=final_instance_count,
        final_unmanaged_count=final_unmanaged_count,
        capacity_error_confirmed=capacity_confirmed,
        closeout_status=(
            "closed_capacity_unavailable_no_instance_created"
            if closeout_succeeded
            else "unresolved"
        ),
        closeout_succeeded=closeout_succeeded,
        future_launch_blocked_for_same_shape=capacity_confirmed,
        future_availability_first_required=capacity_confirmed,
        blockers=blockers,
        warnings=[
            "termination is not required when Lambda rejects launch before instance creation",
            (
                "same fixed-shape retry requires fresh availability evidence "
                "and operator risk acceptance"
            ),
        ],
    )


def build_lambda_capacity_error_closeout_from_paths(
    *,
    m039_workdir: str | Path,
    post_discovery: str | Path,
) -> LambdaCapacityErrorCloseoutReport:
    workdir = Path(m039_workdir)
    report = load_lambda_m029_report(workdir / "report.json")
    transport_error_path = workdir / "transport-error.json"
    spend_path = workdir / "spend-audit.json"
    return build_lambda_capacity_error_closeout(
        m039_report=report,
        transport_error=(
            load_lambda_transport_error_persistence_record(transport_error_path)
            if transport_error_path.exists()
            else None
        ),
        post_discovery=load_lambda_live_discovery_report(post_discovery),
        spend_audit=(
            LambdaM029SpendAuditReport.model_validate_json(
                spend_path.read_text(encoding="utf-8")
            )
            if spend_path.exists()
            else None
        ),
    )


def _is_capacity_message(message: str | None) -> bool:
    if not message:
        return False
    lowered = message.lower()
    return "capacity" in lowered and any(
        term in lowered for term in ("not enough", "unavailable", "insufficient")
    )


def load_lambda_capacity_error_closeout(
    path: str | Path,
) -> LambdaCapacityErrorCloseoutReport:
    return LambdaCapacityErrorCloseoutReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_error_closeout(
    path: str | Path,
    report: LambdaCapacityErrorCloseoutReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
