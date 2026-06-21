"""Planning-only Lambda price reconciliation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.launch_plan import LambdaLaunchPlan, load_lambda_launch_plan
from decodilo.lambda_cloud.launch_shape_resolution import (
    LambdaLaunchShapeResolutionReport,
    load_lambda_launch_shape_resolution_report,
)
from decodilo.lambda_cloud.shape_matcher import (
    LambdaShapeMatch,
    load_discovery_any,
    match_lambda_shape,
)
from decodilo.pricing.snapshots import PriceSnapshot, load_price_snapshot

LambdaPriceSourceStatus = Literal["fresh", "stale", "sample", "missing", "ambiguous"]
LambdaPriceRisk = Literal[
    "sample_price",
    "stale_price",
    "missing_price",
    "ambiguous_price",
    "budget_exceeded",
]


class LambdaPriceReconciliationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    price_snapshot_id: str
    price_snapshot_source_type: str
    price_snapshot_age_days: float | None
    is_sample_data: bool
    allow_sample_prices: bool = False
    allow_stale_prices: bool = False
    selected_price_record_id: str | None = None
    selected_gpu_type: str
    selected_gpus_per_instance: int
    selected_region: str | None = None
    price_per_gpu_hour: float | None = None
    price_per_instance_hour: float | None = None
    planned_instances: int = Field(ge=0)
    planned_gpus: int = Field(ge=0)
    planned_hours: float = Field(gt=0)
    base_estimated_cost: float = Field(ge=0)
    safety_buffer_percentage: float = Field(ge=0)
    safety_buffer_adjusted_cost: float = Field(ge=0)
    max_run_budget: float = Field(ge=0)
    starting_credits: float = Field(ge=0)
    projected_remaining_credits: float
    price_source_status: LambdaPriceSourceStatus
    price_reconciliation_passed: bool
    price_risks: list[LambdaPriceRisk] = Field(default_factory=list)
    shape_match: LambdaShapeMatch
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def reconcile_lambda_price(
    *,
    discovery_report_path: str | Path,
    price_snapshot: PriceSnapshot,
    launch_plan: LambdaLaunchPlan,
    gpu_type: str,
    credits: float,
    planned_hours: float | None = None,
    max_run_budget: float | None = None,
    safety_buffer_percentage: float = 15.0,
    allow_sample_prices: bool = False,
    allow_stale_prices: bool = False,
    stale_after_days: float = 7.0,
    shape_resolution: LambdaLaunchShapeResolutionReport | None = None,
) -> LambdaPriceReconciliationReport:
    discovery = load_discovery_any(discovery_report_path)
    gpus = launch_plan.nodes[0].gpus_per_instance if launch_plan.nodes else 0
    hours = planned_hours if planned_hours is not None else launch_plan.planned_hours
    budget = max_run_budget if max_run_budget is not None else launch_plan.max_run_budget
    match = (
        _match_from_shape_resolution(
            shape_resolution,
            price_snapshot=price_snapshot,
            launch_plan=launch_plan,
            gpu_type=gpu_type,
            gpus=gpus,
        )
        if shape_resolution is not None
        else match_lambda_shape(
            discovery=discovery,
            price_snapshot=price_snapshot,
            requested_gpu_type=gpu_type,
            requested_gpus_per_instance=gpus,
            requested_region=launch_plan.region,
            requested_instance_type=launch_plan.instance_type,
        )
    )
    warnings: list[str] = [*match.warnings]
    errors: list[str] = [*match.errors]
    risks: list[LambdaPriceRisk] = []
    age_days = _snapshot_age_days(price_snapshot)
    source_status: LambdaPriceSourceStatus = "fresh"
    if price_snapshot.is_sample_data:
        source_status = "sample"
        risks.append("sample_price")
        message = "price snapshot is sample data"
        if allow_sample_prices:
            warnings.append(message)
        else:
            errors.append(message)
    if age_days is not None and age_days > stale_after_days:
        source_status = "stale" if source_status == "fresh" else source_status
        risks.append("stale_price")
        message = f"price snapshot is stale: {age_days:.1f} days old"
        if allow_stale_prices:
            warnings.append(message)
        else:
            errors.append(message)
    if match.match_status in {"missing", "discovered_but_no_price", "priced_but_not_discovered"}:
        risks.append("missing_price")
    if match.match_status == "ambiguous":
        risks.append("ambiguous_price")
        source_status = "ambiguous"
    price_per_instance = match.price_per_instance_hour or 0.0
    base_cost = launch_plan.node_count * price_per_instance * hours
    buffer_adjusted = base_cost * (1 + safety_buffer_percentage / 100.0)
    projected_remaining = credits - buffer_adjusted
    if buffer_adjusted > budget:
        risks.append("budget_exceeded")
        errors.append("safety-buffer-adjusted cost exceeds max_run_budget")
    if projected_remaining < 0:
        errors.append("projected remaining credits would be negative")
    return LambdaPriceReconciliationReport(
        price_snapshot_id=price_snapshot.snapshot_id,
        price_snapshot_source_type=str(price_snapshot.source_type.value),
        price_snapshot_age_days=age_days,
        is_sample_data=price_snapshot.is_sample_data,
        allow_sample_prices=allow_sample_prices,
        allow_stale_prices=allow_stale_prices,
        selected_price_record_id=match.matched_price_record_id,
        selected_gpu_type=gpu_type,
        selected_gpus_per_instance=gpus,
        selected_region=launch_plan.region,
        price_per_gpu_hour=match.price_per_gpu_hour,
        price_per_instance_hour=match.price_per_instance_hour,
        planned_instances=launch_plan.node_count,
        planned_gpus=launch_plan.node_count * gpus,
        planned_hours=hours,
        base_estimated_cost=base_cost,
        safety_buffer_percentage=safety_buffer_percentage,
        safety_buffer_adjusted_cost=buffer_adjusted,
        max_run_budget=budget,
        starting_credits=credits,
        projected_remaining_credits=projected_remaining,
        price_source_status=source_status,
        price_reconciliation_passed=not errors,
        price_risks=sorted(set(risks)),
        shape_match=match,
        warnings=warnings,
        errors=errors,
    )


def reconcile_lambda_price_from_paths(
    *,
    discovery_report: str | Path,
    price_snapshot: str | Path,
    launch_plan: str | Path,
    gpu_type: str,
    credits: float,
    planned_hours: float | None = None,
    max_run_budget: float | None = None,
    safety_buffer_percentage: float = 15.0,
    allow_sample_prices: bool = False,
    allow_stale_prices: bool = False,
    shape_resolution: str | Path | None = None,
) -> LambdaPriceReconciliationReport:
    return reconcile_lambda_price(
        discovery_report_path=discovery_report,
        price_snapshot=load_price_snapshot(price_snapshot),
        launch_plan=load_lambda_launch_plan(launch_plan),
        gpu_type=gpu_type,
        credits=credits,
        planned_hours=planned_hours,
        max_run_budget=max_run_budget,
        safety_buffer_percentage=safety_buffer_percentage,
        allow_sample_prices=allow_sample_prices,
        allow_stale_prices=allow_stale_prices,
        shape_resolution=None
        if shape_resolution is None
        else load_lambda_launch_shape_resolution_report(shape_resolution),
    )


def _match_from_shape_resolution(
    resolution: LambdaLaunchShapeResolutionReport,
    *,
    price_snapshot: PriceSnapshot,
    launch_plan: LambdaLaunchPlan,
    gpu_type: str,
    gpus: int,
) -> LambdaShapeMatch:
    if not resolution.first_launch_allowed_by_shape_evidence:
        return LambdaShapeMatch(
            requested_gpu_type=gpu_type,
            requested_gpus_per_instance=gpus,
            requested_region=launch_plan.region,
            requested_instance_type=launch_plan.instance_type,
            discovery_source="shape_resolution",
            live_api_used=False,
            price_snapshot_id=price_snapshot.snapshot_id,
            match_status="missing",
            errors=list(resolution.errors),
        )
    price_record = resolution.matched_price_record or {}
    return LambdaShapeMatch(
        requested_gpu_type=gpu_type,
        requested_gpus_per_instance=gpus,
        requested_region=launch_plan.region,
        requested_instance_type=launch_plan.instance_type,
        matched_instance_type=str(
            price_record.get("instance_type") or resolution.planned_instance_type_or_shape
        ),
        matched_shape=resolution.matched_product_catalog_record,
        matched_price_record_id=price_record.get("record_id"),
        price_per_gpu_hour=price_record.get("price_per_gpu_hour"),
        price_per_instance_hour=price_record.get("price_per_instance_hour"),
        discovery_source="product_catalog_and_price_snapshot",
        live_api_used=False,
        price_snapshot_id=price_snapshot.snapshot_id,
        match_status="matched",
        warnings=[
            "shape resolved from product catalog and non-sample price evidence",
            *resolution.warnings,
        ],
    )



def _snapshot_age_days(snapshot: PriceSnapshot) -> float | None:
    try:
        captured = datetime.fromisoformat(snapshot.captured_at_utc.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0.0, (datetime.now(timezone.utc) - captured).total_seconds() / 86400.0)


def load_lambda_price_reconciliation_report(path: str | Path) -> LambdaPriceReconciliationReport:
    return LambdaPriceReconciliationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_price_reconciliation_report(
    path: str | Path,
    report: LambdaPriceReconciliationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
