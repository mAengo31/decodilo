"""M028 final prelaunch state snapshot."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.m020_report import LambdaM020ReadinessReport, load_lambda_m020_report


class LambdaFinalPrelaunchStateSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    snapshot_id: str = "lambda-final-prelaunch-state-snapshot-m028"
    source_discovery_ref: str
    m020_report_ref: str
    discovery_age_seconds: float | None = None
    required_endpoint_success: bool
    endpoint_count_succeeded: int
    endpoint_count_unsupported_optional: int
    unmanaged_count: int
    unmanaged_billable_count: int
    planned_instance_type: str
    planned_region: str
    planned_gpu_type: str
    planned_gpus_per_instance: int
    selected_price_record_id: str | None
    safety_buffer_adjusted_cost: float
    snapshot_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaFinalPrelaunchStateSnapshot:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M028 state snapshot cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_final_prelaunch_state_snapshot(
    *,
    discovery_report: str | Path,
    m020_report: str | Path | LambdaM020ReadinessReport,
) -> LambdaFinalPrelaunchStateSnapshot:
    discovery = load_lambda_live_discovery_report(discovery_report)
    m020 = (
        m020_report
        if isinstance(m020_report, LambdaM020ReadinessReport)
        else load_lambda_m020_report(m020_report)
    )
    price = m020.price_reconciliation
    resources = m020.resource_reconciliation
    blockers: list[str] = []
    if not discovery.required_endpoint_success:
        blockers.append("required read-only endpoint failed")
    if resources.unmanaged_billable_instances:
        blockers.append("unmanaged billable resources present")
    if not price.selected_price_record_id:
        blockers.append("selected price record missing")
    if not price.price_reconciliation_passed:
        blockers.append("price reconciliation did not pass")
    if not resources.resource_reconciliation_passed:
        blockers.append("resource reconciliation did not pass")
    report_ref = (
        "<in-memory>"
        if isinstance(m020_report, LambdaM020ReadinessReport)
        else str(m020_report)
    )
    return LambdaFinalPrelaunchStateSnapshot(
        source_discovery_ref=str(discovery_report),
        m020_report_ref=report_ref,
        discovery_age_seconds=_age_seconds(discovery.created_at_utc),
        required_endpoint_success=discovery.required_endpoint_success,
        endpoint_count_succeeded=discovery.endpoint_count_succeeded,
        endpoint_count_unsupported_optional=discovery.endpoint_count_unsupported_optional,
        unmanaged_count=resources.unmanaged_instances,
        unmanaged_billable_count=resources.unmanaged_billable_instances,
        planned_instance_type=price.shape_match.requested_instance_type
        or price.shape_match.matched_instance_type
        or "unknown",
        planned_region=price.selected_region or "unknown",
        planned_gpu_type=price.selected_gpu_type,
        planned_gpus_per_instance=price.selected_gpus_per_instance,
        selected_price_record_id=price.selected_price_record_id,
        safety_buffer_adjusted_cost=price.safety_buffer_adjusted_cost,
        snapshot_passed=not blockers,
        blockers=blockers,
        warnings=["M028 state snapshot is review evidence only."],
    )


def _age_seconds(created_at_utc: str | None) -> float | None:
    if created_at_utc is None:
        return None
    try:
        created = datetime.fromisoformat(created_at_utc.replace("Z", "+00:00"))
    except ValueError:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - created).total_seconds())


def load_lambda_final_prelaunch_state_snapshot(
    path: str | Path,
) -> LambdaFinalPrelaunchStateSnapshot:
    return LambdaFinalPrelaunchStateSnapshot.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_final_prelaunch_state_snapshot(
    path: str | Path,
    snapshot: LambdaFinalPrelaunchStateSnapshot,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(snapshot.to_json(), encoding="utf-8")
