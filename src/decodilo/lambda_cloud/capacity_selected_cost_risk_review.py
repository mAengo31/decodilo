"""Cost and risk review for the capacity-history-selected Lambda candidate."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_history import load_lambda_capacity_history
from decodilo.lambda_cloud.capacity_history_aware_selector import (
    load_lambda_capacity_history_aware_selector,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import SnapshotPriceRecord, load_price_snapshot

CAPACITY_SELECTED_CANDIDATE = "gpu_8x_a100_80gb_sxm4"
CAPACITY_SELECTED_PRIOR_EXCLUDED_CANDIDATE = "gpu_1x_h100_pcie"


class LambdaCapacitySelectedCostRiskReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selected_candidate: str | None = None
    candidate_source: str | None = None
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    selected_region: str | None = None
    price_per_gpu_hour: float | None = None
    price_per_instance_hour: float | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    max_budget: float = 50.0
    prior_excluded_candidate: str | None = None
    prior_exclusion_reason: str | None = None
    candidate_larger_than_lifecycle_smoke_minimum: bool = False
    live_availability_status: str
    catalog_backed_not_live_confirmed: bool = False
    non_sample_price: bool
    response_loss_controls_passed: bool
    existing_ssh_key_available: bool
    cost_risk_review_passed: bool
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCapacitySelectedCostRiskReview:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("capacity-selected cost/risk review cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaCapacitySelectedCostRiskReviewReport = LambdaCapacitySelectedCostRiskReview


def build_lambda_capacity_selected_cost_risk_review_from_paths(
    *,
    selector_output: str | Path,
    price_snapshot: str | Path,
    capacity_history: str | Path,
    response_loss_controls: str | Path | None = None,
    ssh_key_selection: str | Path | None = None,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaCapacitySelectedCostRiskReview:
    selector = load_lambda_capacity_history_aware_selector(selector_output)
    snapshot = load_price_snapshot(price_snapshot)
    history = load_lambda_capacity_history(capacity_history)
    controls_passed = True
    if response_loss_controls is not None and Path(response_loss_controls).exists():
        controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
        controls_passed = controls.controls_passed and controls.no_auto_launch_retry
    ssh_available = True
    if ssh_key_selection is not None and Path(ssh_key_selection).exists():
        ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
        ssh_available = ssh.selection_passed
    return build_lambda_capacity_selected_cost_risk_review(
        selected_shape=(
            None
            if selector.selected_candidate is None
            else selector.selected_candidate.shape
        ),
        candidate_source=selector.selected_candidate_source,
        selected_region=(
            None
            if selector.selected_candidate is None
            else selector.selected_candidate.region
        ),
        live_available=(
            False
            if selector.selected_candidate is None
            else selector.selected_candidate.live_available
        ),
        prior_exclusion_reason=selector.exclusion_reasons.get(
            CAPACITY_SELECTED_PRIOR_EXCLUDED_CANDIDATE
        ),
        price_snapshot_records=snapshot.records,
        non_sample_price=not snapshot.is_sample_data,
        capacity_history_shapes=set(history.shapes_with_capacity_errors),
        response_loss_controls_passed=controls_passed,
        existing_ssh_key_available=ssh_available,
        max_budget=max_budget,
        planned_runtime_minutes=planned_runtime_minutes,
        safety_buffer_multiplier=safety_buffer_multiplier,
    )


def build_lambda_capacity_selected_cost_risk_review(
    *,
    selected_shape: str | None,
    candidate_source: str | None,
    selected_region: str | None,
    live_available: bool,
    prior_exclusion_reason: str | None,
    price_snapshot_records: list[SnapshotPriceRecord],
    non_sample_price: bool,
    capacity_history_shapes: set[str],
    response_loss_controls_passed: bool = True,
    existing_ssh_key_available: bool = True,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaCapacitySelectedCostRiskReview:
    blockers: list[str] = []
    warnings = [
        "capacity-selected review is future-only and does not authorize launch",
    ]
    if not non_sample_price:
        blockers.append("sample_price_snapshot_cannot_authorize_capacity_selected_review")
    if selected_shape != CAPACITY_SELECTED_CANDIDATE:
        blockers.append("selected_candidate_is_not_current_capacity_history_selected_a100")
    if planned_runtime_minutes > 30:
        blockers.append("planned_runtime_exceeds_30_minutes")
    if CAPACITY_SELECTED_PRIOR_EXCLUDED_CANDIDATE not in capacity_history_shapes:
        blockers.append("prior_h100_pcie_capacity_failure_missing_from_history")
    if prior_exclusion_reason != "recent_capacity_error_excluded":
        blockers.append("prior_candidate_recent_capacity_exclusion_missing")
    if not response_loss_controls_passed:
        blockers.append("response_loss_controls_not_passed")
    if not existing_ssh_key_available:
        blockers.append("existing_ssh_key_selection_required")
    record = _find_price_record(price_snapshot_records, CAPACITY_SELECTED_CANDIDATE)
    if record is None:
        blockers.append("selected_candidate_price_missing")
    estimate = _estimate_cost(record, planned_runtime_minutes)
    buffered = None if estimate is None else round(estimate * safety_buffer_multiplier, 8)
    if buffered is not None and buffered >= max_budget:
        blockers.append("buffered_estimated_cost_not_below_max_budget")
    larger_than_minimum = bool(record is not None and record.gpus_per_instance > 1)
    if larger_than_minimum:
        warnings.append("selected candidate is larger than needed for lifecycle smoke")
    catalog_only = candidate_source == "product_catalog" and not live_available
    if catalog_only:
        warnings.append("selected candidate is catalog-backed, not live-availability-backed")
    return LambdaCapacitySelectedCostRiskReview(
        selected_candidate=CAPACITY_SELECTED_CANDIDATE if record is not None else None,
        candidate_source=candidate_source,
        gpu_type=None if record is None else record.gpu_type,
        gpus_per_instance=None if record is None else record.gpus_per_instance,
        selected_region=selected_region,
        price_per_gpu_hour=None if record is None else record.price_per_gpu_hour,
        price_per_instance_hour=None if record is None else record.price_per_instance_hour,
        estimated_30min_cost=estimate,
        buffered_estimated_30min_cost=buffered,
        max_budget=max_budget,
        prior_excluded_candidate=CAPACITY_SELECTED_PRIOR_EXCLUDED_CANDIDATE,
        prior_exclusion_reason=prior_exclusion_reason,
        candidate_larger_than_lifecycle_smoke_minimum=larger_than_minimum,
        live_availability_status="live_available" if live_available else "catalog_only",
        catalog_backed_not_live_confirmed=catalog_only,
        non_sample_price=non_sample_price,
        response_loss_controls_passed=response_loss_controls_passed,
        existing_ssh_key_available=existing_ssh_key_available,
        cost_risk_review_passed=not blockers,
        warnings=warnings,
        blockers=sorted(set(blockers)),
    )


def _find_price_record(
    records: list[SnapshotPriceRecord],
    instance_type: str,
) -> SnapshotPriceRecord | None:
    return next(
        (
            record
            for record in records
            if record.provider == "lambda" and record.instance_type == instance_type
        ),
        None,
    )


def _estimate_cost(
    record: SnapshotPriceRecord | None,
    planned_runtime_minutes: int,
) -> float | None:
    if record is None:
        return None
    return round(record.price_per_instance_hour * planned_runtime_minutes / 60, 8)


def load_lambda_capacity_selected_cost_risk_review(
    path: str | Path,
) -> LambdaCapacitySelectedCostRiskReview:
    return LambdaCapacitySelectedCostRiskReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_selected_cost_risk_review(
    path: str | Path,
    report: LambdaCapacitySelectedCostRiskReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
