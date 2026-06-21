"""Lower-cost Lambda price reconciliation for future launch review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot


class LambdaLowerCostPriceReconciliationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selected_shape: Literal["gpu_1x_h100_pcie"] = "gpu_1x_h100_pcie"
    price_per_gpu_hour: float | None = None
    price_per_instance_hour: float | None = None
    planned_hours: float = 0.5
    base_estimated_cost: float | None = None
    safety_buffer_multiplier: float = 1.15
    safety_buffer_adjusted_cost: float | None = None
    max_budget: float = 50.0
    price_reconciliation_passed: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostPriceReconciliationReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost price reconciliation cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def reconcile_lambda_lower_cost_price(
    *,
    price_snapshot: PriceSnapshot,
    shape: str = "gpu_1x_h100_pcie",
    planned_hours: float = 0.5,
    max_budget: float = 50.0,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaLowerCostPriceReconciliationReport:
    errors: list[str] = []
    warnings = [
        "price evidence is product-catalog planning evidence, not live availability",
        "M037R price reconciliation does not authorize execution",
    ]
    if shape != "gpu_1x_h100_pcie":
        errors.append("M037R lower-cost reconciliation only supports gpu_1x_h100_pcie")
    if price_snapshot.is_sample_data:
        errors.append("sample_price_snapshot_cannot_support_future_lower_cost_review")
    matches = [record for record in price_snapshot.records if record.instance_type == shape]
    if not matches:
        errors.append("selected_lower_cost_shape_missing_from_price_snapshot")
    if len(matches) > 1:
        errors.append("selected_lower_cost_shape_price_is_ambiguous")
    record = matches[0] if len(matches) == 1 else None
    base_cost = None if record is None else round(record.price_per_instance_hour * planned_hours, 8)
    adjusted = (
        None
        if base_cost is None
        else round(base_cost * safety_buffer_multiplier, 8)
    )
    if adjusted is not None and adjusted >= max_budget:
        errors.append("lower_cost_shape_estimate_exceeds_budget")
    return LambdaLowerCostPriceReconciliationReport(
        price_per_gpu_hour=None if record is None else record.price_per_gpu_hour,
        price_per_instance_hour=None if record is None else record.price_per_instance_hour,
        planned_hours=planned_hours,
        base_estimated_cost=base_cost,
        safety_buffer_multiplier=safety_buffer_multiplier,
        safety_buffer_adjusted_cost=adjusted,
        max_budget=max_budget,
        price_reconciliation_passed=not errors,
        warnings=warnings,
        errors=errors,
    )


def reconcile_lambda_lower_cost_price_from_path(
    *,
    price_snapshot: str | Path,
    shape: str = "gpu_1x_h100_pcie",
    planned_hours: float = 0.5,
    max_budget: float = 50.0,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaLowerCostPriceReconciliationReport:
    return reconcile_lambda_lower_cost_price(
        price_snapshot=load_price_snapshot(price_snapshot),
        shape=shape,
        planned_hours=planned_hours,
        max_budget=max_budget,
        safety_buffer_multiplier=safety_buffer_multiplier,
    )


def lower_cost_price_record(
    price_snapshot: PriceSnapshot,
    shape: str = "gpu_1x_h100_pcie",
) -> SnapshotPriceRecord | None:
    matches = [record for record in price_snapshot.records if record.instance_type == shape]
    return matches[0] if len(matches) == 1 else None


def load_lambda_lower_cost_price_reconciliation(
    path: str | Path,
) -> LambdaLowerCostPriceReconciliationReport:
    return LambdaLowerCostPriceReconciliationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_price_reconciliation(
    path: str | Path,
    report: LambdaLowerCostPriceReconciliationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
