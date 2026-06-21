"""M035 launch-shape strategy review for lifecycle-only smoke attempts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot

LambdaLaunchShapeStrategy = Literal[
    "keep_current_shape",
    "switch_to_lower_cost_shape",
    "require_operator_selection",
    "unavailable",
]


class LambdaLaunchShapeStrategyReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    current_shape: str
    alternative_shapes: list[dict[str, object]] = Field(default_factory=list)
    cheapest_safe_shape_if_available: dict[str, object] | None = None
    recommended_shape_strategy: LambdaLaunchShapeStrategy
    estimated_cost_current_30_min: float | None = None
    estimated_cost_alternative_30_min: float | None = None
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLaunchShapeStrategyReview:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M035 shape strategy cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_launch_shape_strategy_review(
    *,
    price_snapshot: PriceSnapshot,
    current_shape: str,
    lifecycle_smoke_only: bool = True,
) -> LambdaLaunchShapeStrategyReview:
    blockers: list[str] = []
    warnings: list[str] = []
    if price_snapshot.is_sample_data:
        blockers.append("sample_price_snapshot_cannot_support_shape_strategy")
    current = _find_record(price_snapshot.records, current_shape)
    if current is None:
        blockers.append("current_shape_missing_from_price_snapshot")
    alternatives = [
        record
        for record in price_snapshot.records
        if record.instance_type != current_shape and record.price_per_instance_hour >= 0
    ]
    alternatives = sorted(alternatives, key=lambda record: record.price_per_instance_hour)
    cheaper = [
        record
        for record in alternatives
        if current is not None
        and record.price_per_instance_hour < current.price_per_instance_hour
    ]
    cheapest = cheaper[0] if cheaper else (alternatives[0] if alternatives else None)
    strategy: LambdaLaunchShapeStrategy
    if blockers:
        strategy = "unavailable"
    elif lifecycle_smoke_only and cheaper:
        strategy = "switch_to_lower_cost_shape"
        warnings.append(
            "lifecycle-only smoke does not require the highest-cost GPU shape"
        )
    elif current is not None:
        strategy = "keep_current_shape"
    else:
        strategy = "require_operator_selection"
    return LambdaLaunchShapeStrategyReview(
        current_shape=current_shape,
        alternative_shapes=[_shape_summary(record) for record in alternatives],
        cheapest_safe_shape_if_available=None if cheapest is None else _shape_summary(cheapest),
        recommended_shape_strategy=strategy,
        estimated_cost_current_30_min=None
        if current is None
        else round(current.price_per_instance_hour * 0.5, 8),
        estimated_cost_alternative_30_min=None
        if cheapest is None
        else round(cheapest.price_per_instance_hour * 0.5, 8),
        limitations=[
            "live availability remains unknown until launch",
            "API instance-type discovery has been inconclusive",
            "shape switch requires updated M020/M028/M029 authorization artifacts",
        ],
        warnings=warnings,
        blockers=blockers,
    )


def build_lambda_launch_shape_strategy_review_from_paths(
    *,
    price_snapshot: str | Path,
    current_shape: str,
) -> LambdaLaunchShapeStrategyReview:
    return build_lambda_launch_shape_strategy_review(
        price_snapshot=load_price_snapshot(price_snapshot),
        current_shape=current_shape,
    )


def _find_record(
    records: list[SnapshotPriceRecord],
    instance_type: str,
) -> SnapshotPriceRecord | None:
    for record in records:
        if record.instance_type == instance_type:
            return record
    return None


def _shape_summary(record: SnapshotPriceRecord) -> dict[str, object]:
    return {
        "instance_type": record.instance_type,
        "gpu_type": record.gpu_type,
        "gpus_per_instance": record.gpus_per_instance,
        "price_per_gpu_hour": record.price_per_gpu_hour,
        "price_per_instance_hour": record.price_per_instance_hour,
        "estimated_cost_30_min": round(record.price_per_instance_hour * 0.5, 8),
        "record_id": record.record_id,
    }


def load_lambda_launch_shape_strategy_review(
    path: str | Path,
) -> LambdaLaunchShapeStrategyReview:
    return LambdaLaunchShapeStrategyReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_launch_shape_strategy_review(
    path: str | Path,
    report: LambdaLaunchShapeStrategyReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
