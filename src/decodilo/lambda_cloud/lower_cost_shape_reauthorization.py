"""M036 lower-cost shape reauthorization review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.support_confirmation_response import (
    LambdaSupportConfirmationResponse,
    load_lambda_support_confirmation_response,
)
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot

LambdaLowerCostShapeDecisionStatus = Literal[
    "keep_current_shape",
    "reauthorize_lower_cost_shape",
    "needs_operator_selection",
    "no_suitable_lower_cost_shape",
]


class LambdaLowerCostShapeCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    shape: str
    gpu_type: str
    gpus_per_instance: int
    price_per_gpu_hour: float
    price_per_instance_hour: float
    estimated_30min_cost: float
    catalog_evidence_ref: str
    support_confirms_available: bool | None = None
    live_availability_unknown: bool = True
    suitability_for_lifecycle_smoke: str = "suitable_pending_future_authorization"


class LambdaLowerCostShapeDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: LambdaLowerCostShapeDecisionStatus
    selected_shape: str | None = None
    requires_future_reauthorization: bool = False
    warnings: list[str] = Field(default_factory=list)


class LambdaLowerCostShapeReauthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    current_shape: str
    current_shape_estimated_30min_cost: float | None = None
    candidates: list[LambdaLowerCostShapeCandidate]
    recommended_candidate: LambdaLowerCostShapeCandidate | None = None
    decision: LambdaLowerCostShapeDecision
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostShapeReauthorization:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost shape review cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_shape_reauthorization(
    *,
    price_snapshot: PriceSnapshot,
    current_shape: str,
    support_response: LambdaSupportConfirmationResponse | None = None,
    operator_selected_shape: str | None = None,
) -> LambdaLowerCostShapeReauthorization:
    blockers: list[str] = []
    if price_snapshot.is_sample_data:
        blockers.append("sample_price_snapshot_cannot_reauthorize_shape")
    current = _find_record(price_snapshot.records, current_shape)
    if current is None:
        blockers.append("current_shape_missing_from_price_snapshot")
    support_available = _support_safe_shape_map(support_response)
    candidates = [
        _candidate(record, support_available)
        for record in sorted(price_snapshot.records, key=lambda item: item.price_per_instance_hour)
        if record.instance_type != current_shape
        and current is not None
        and record.price_per_instance_hour < current.price_per_instance_hour
        and support_available.get(record.instance_type, True) is not False
    ]
    selected = None
    if operator_selected_shape is not None:
        selected = next(
            (candidate for candidate in candidates if candidate.shape == operator_selected_shape),
            None,
        )
        if selected is None:
            blockers.append("operator_selected_shape_not_suitable")
    else:
        selected = candidates[0] if candidates else None
    if blockers:
        status: LambdaLowerCostShapeDecisionStatus = "needs_operator_selection"
    elif selected is not None:
        status = "reauthorize_lower_cost_shape"
    elif candidates:
        status = "needs_operator_selection"
    else:
        status = "keep_current_shape" if current is not None else "no_suitable_lower_cost_shape"
    return LambdaLowerCostShapeReauthorization(
        current_shape=current_shape,
        current_shape_estimated_30min_cost=None
        if current is None
        else round(current.price_per_instance_hour * 0.5, 8),
        candidates=candidates,
        recommended_candidate=selected,
        decision=LambdaLowerCostShapeDecision(
            status=status,
            selected_shape=None if selected is None else selected.shape,
            requires_future_reauthorization=status == "reauthorize_lower_cost_shape",
            warnings=[
                "shape switch requires future M020/M028/M029 regeneration",
                "live availability remains unknown until launch",
            ],
        ),
        blockers=blockers,
    )


def build_lambda_lower_cost_shape_reauthorization_from_paths(
    *,
    price_snapshot: str | Path,
    current_shape: str,
    support_response: str | Path | None = None,
    operator_selected_shape: str | None = None,
) -> LambdaLowerCostShapeReauthorization:
    return build_lambda_lower_cost_shape_reauthorization(
        price_snapshot=load_price_snapshot(price_snapshot),
        current_shape=current_shape,
        support_response=None
        if support_response is None
        else load_lambda_support_confirmation_response(support_response),
        operator_selected_shape=operator_selected_shape,
    )


def _candidate(
    record: SnapshotPriceRecord,
    support_available: dict[str, bool],
) -> LambdaLowerCostShapeCandidate:
    return LambdaLowerCostShapeCandidate(
        shape=record.instance_type,
        gpu_type=record.gpu_type,
        gpus_per_instance=record.gpus_per_instance,
        price_per_gpu_hour=record.price_per_gpu_hour,
        price_per_instance_hour=record.price_per_instance_hour,
        estimated_30min_cost=round(record.price_per_instance_hour * 0.5, 8),
        catalog_evidence_ref=record.record_id,
        support_confirms_available=support_available.get(record.instance_type),
    )


def _find_record(
    records: list[SnapshotPriceRecord],
    instance_type: str,
) -> SnapshotPriceRecord | None:
    for record in records:
        if record.instance_type == instance_type:
            return record
    return None


def _support_safe_shape_map(
    response: LambdaSupportConfirmationResponse | None,
) -> dict[str, bool]:
    if response is None:
        return {}
    answers = response.answer_map()
    result: dict[str, bool] = {}
    for key in [
        "safe_lifecycle_shape",
        "h100_pcie_1x_supported",
        "lower_cost_non_h100_shape",
    ]:
        answer = answers.get(key)
        if answer is None:
            continue
        structured = answer.structured_value
        shape = structured.get("shape")
        available = structured.get("available")
        if shape is not None and isinstance(available, bool):
            result[str(shape)] = available
    return result


def load_lambda_lower_cost_shape_reauthorization(
    path: str | Path,
) -> LambdaLowerCostShapeReauthorization:
    return LambdaLowerCostShapeReauthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_shape_reauthorization(
    path: str | Path,
    report: LambdaLowerCostShapeReauthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
