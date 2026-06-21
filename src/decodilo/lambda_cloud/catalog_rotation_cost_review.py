"""Cost review for catalog-rotation Lambda launch candidates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.catalog_candidate_rotation import (
    load_lambda_catalog_candidate_rotation,
)
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot

CATALOG_ROTATION_SELECTED_CANDIDATE = "gpu_8x_a100_80gb_sxm4"
CATALOG_ROTATION_PRIOR_FAILED_CANDIDATE = "gpu_1x_h100_pcie"


class LambdaCatalogRotationCostReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selected_candidate: str | None = None
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    price_per_gpu_hour: float | None = None
    price_per_instance_hour: float | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    prior_failed_candidate: str = CATALOG_ROTATION_PRIOR_FAILED_CANDIDATE
    prior_failed_buffered_30min_cost: float | None = None
    incremental_cost_vs_prior_failed_candidate: float | None = None
    max_budget: float = 50.0
    planned_runtime_minutes: int = 30
    non_sample_price: bool
    cost_review_passed: bool
    candidate_source: Literal["product_catalog"] = "product_catalog"
    live_availability_backed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCatalogRotationCostReview:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("catalog-rotation cost review cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaCatalogRotationCostReviewReport = LambdaCatalogRotationCostReview


def build_lambda_catalog_rotation_cost_review_from_paths(
    *,
    rotation_rank: str | Path,
    price_snapshot: str | Path,
    selected_candidate: str = CATALOG_ROTATION_SELECTED_CANDIDATE,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaCatalogRotationCostReview:
    rotation = load_lambda_catalog_candidate_rotation(rotation_rank)
    snapshot = load_price_snapshot(price_snapshot)
    return build_lambda_catalog_rotation_cost_review(
        rotation_selected_shape=(
            None if rotation.selected_candidate is None else rotation.selected_candidate.shape
        ),
        price_snapshot=snapshot,
        selected_candidate=selected_candidate,
        max_budget=max_budget,
        planned_runtime_minutes=planned_runtime_minutes,
        safety_buffer_multiplier=safety_buffer_multiplier,
    )


def build_lambda_catalog_rotation_cost_review(
    *,
    rotation_selected_shape: str | None,
    price_snapshot: PriceSnapshot,
    selected_candidate: str = CATALOG_ROTATION_SELECTED_CANDIDATE,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaCatalogRotationCostReview:
    blockers: list[str] = []
    warnings = [
        "catalog-rotation candidate is catalog-backed, not live-availability-backed",
        "M044 cost review is future-review only and does not authorize launch",
    ]
    if price_snapshot.is_sample_data:
        blockers.append("sample_price_snapshot_cannot_authorize_catalog_rotation")
    if rotation_selected_shape != selected_candidate:
        blockers.append("rotation_selected_candidate_does_not_match_m044_candidate")
    if planned_runtime_minutes > 30:
        blockers.append("planned_runtime_exceeds_30_minutes")
    selected_record = _find_price_record(price_snapshot, selected_candidate)
    prior_record = _find_price_record(price_snapshot, CATALOG_ROTATION_PRIOR_FAILED_CANDIDATE)
    if selected_record is None:
        blockers.append("selected_candidate_price_missing")
    if prior_record is None:
        blockers.append("prior_failed_candidate_price_missing")
    selected_estimate = _estimate_cost(selected_record, planned_runtime_minutes)
    selected_buffered = _buffered_cost(
        selected_record,
        planned_runtime_minutes,
        safety_buffer_multiplier,
    )
    prior_buffered = _buffered_cost(
        prior_record,
        planned_runtime_minutes,
        safety_buffer_multiplier,
    )
    if selected_buffered is not None and selected_buffered >= max_budget:
        blockers.append("buffered_estimated_cost_not_below_max_budget")
    if selected_record is not None and selected_record.gpus_per_instance > 1:
        warnings.append("selected candidate is materially larger than lifecycle-smoke minimum")
    incremental = (
        None
        if selected_buffered is None or prior_buffered is None
        else round(selected_buffered - prior_buffered, 8)
    )
    return LambdaCatalogRotationCostReview(
        selected_candidate=selected_candidate if selected_record is not None else None,
        gpu_type=None if selected_record is None else selected_record.gpu_type,
        gpus_per_instance=None if selected_record is None else selected_record.gpus_per_instance,
        price_per_gpu_hour=None if selected_record is None else selected_record.price_per_gpu_hour,
        price_per_instance_hour=(
            None if selected_record is None else selected_record.price_per_instance_hour
        ),
        estimated_30min_cost=selected_estimate,
        buffered_estimated_30min_cost=selected_buffered,
        prior_failed_buffered_30min_cost=prior_buffered,
        incremental_cost_vs_prior_failed_candidate=incremental,
        max_budget=max_budget,
        planned_runtime_minutes=planned_runtime_minutes,
        non_sample_price=not price_snapshot.is_sample_data,
        cost_review_passed=not blockers,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def _find_price_record(
    price_snapshot: PriceSnapshot,
    instance_type: str,
) -> SnapshotPriceRecord | None:
    return next(
        (
            record
            for record in price_snapshot.records
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


def _buffered_cost(
    record: SnapshotPriceRecord | None,
    planned_runtime_minutes: int,
    safety_buffer_multiplier: float,
) -> float | None:
    estimate = _estimate_cost(record, planned_runtime_minutes)
    return None if estimate is None else round(estimate * safety_buffer_multiplier, 8)


def load_lambda_catalog_rotation_cost_review(
    path: str | Path,
) -> LambdaCatalogRotationCostReview:
    return LambdaCatalogRotationCostReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_rotation_cost_review(
    path: str | Path,
    report: LambdaCatalogRotationCostReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
