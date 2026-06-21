"""Rank alternative catalog candidates after Lambda capacity errors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_history import (
    load_lambda_capacity_history,
)
from decodilo.lambda_cloud.catalog_candidate_policy import (
    LambdaCatalogCandidatePolicy,
    default_lambda_catalog_candidate_policy,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import PriceSnapshot, load_price_snapshot

LambdaCatalogCandidateSelectionStatus = Literal[
    "selected_alternative_catalog_candidate",
    "no_alternative_candidate",
    "operator_selection_required",
    "wait_for_live_availability_recommended",
]


class LambdaCatalogRotationCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    rank: int
    shape: str
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    region: str | None = "us-west-1"
    price_per_instance_hour: float | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    source: Literal["product_catalog"] = "product_catalog"
    excluded: bool = False
    exclusion_reason: str | None = None
    strand_payload_compatible: bool = True
    filesystem_required: bool = False


class LambdaCatalogCandidateRotationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    candidates_ranked: list[LambdaCatalogRotationCandidate] = Field(default_factory=list)
    excluded_candidates: list[LambdaCatalogRotationCandidate] = Field(default_factory=list)
    selected_candidate: LambdaCatalogRotationCandidate | None = None
    selection_status: LambdaCatalogCandidateSelectionStatus
    operator_risk_acceptance_required: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCatalogCandidateRotationReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("catalog candidate rotation cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_catalog_candidate_rotation(
    *,
    price_snapshot: PriceSnapshot,
    capacity_error_shapes: set[str],
    ssh_key_selection_passed: bool,
    policy: LambdaCatalogCandidatePolicy | None = None,
) -> LambdaCatalogCandidateRotationReport:
    policy = policy or default_lambda_catalog_candidate_policy()
    blockers: list[str] = []
    if price_snapshot.is_sample_data:
        blockers.append("sample_price_snapshot_cannot_rank_catalog_rotation")
    if not ssh_key_selection_passed:
        blockers.append("existing_ssh_key_selection_required")
    ranked: list[LambdaCatalogRotationCandidate] = []
    excluded: list[LambdaCatalogRotationCandidate] = []
    for record in price_snapshot.records:
        if record.provider != "lambda":
            continue
        estimated = _estimate(record.price_per_instance_hour, policy.planned_hours)
        buffered = _buffered(
            record.price_per_instance_hour,
            policy.planned_hours,
            policy.safety_buffer_multiplier,
        )
        exclusion_reason = None
        if buffered is None:
            exclusion_reason = "missing_price"
        elif buffered >= policy.max_budget:
            exclusion_reason = "buffered_cost_not_below_budget"
        elif (
            policy.exclude_recent_capacity_error_shapes
            and not policy.allow_operator_override_for_failed_shape
            and record.instance_type in capacity_error_shapes
        ):
            exclusion_reason = "recent_capacity_error_shape_excluded"
        candidate = LambdaCatalogRotationCandidate(
            rank=0,
            shape=record.instance_type,
            gpu_type=record.gpu_type,
            gpus_per_instance=record.gpus_per_instance,
            region=record.region or "us-west-1",
            price_per_instance_hour=record.price_per_instance_hour,
            estimated_30min_cost=estimated,
            buffered_estimated_30min_cost=buffered,
            excluded=exclusion_reason is not None,
            exclusion_reason=exclusion_reason,
        )
        if exclusion_reason is None:
            ranked.append(candidate)
        else:
            excluded.append(candidate)
    ranked = [
        candidate.model_copy(update={"rank": index + 1})
        for index, candidate in enumerate(sorted(ranked, key=_rank_key))
    ]
    excluded = [
        candidate.model_copy(update={"rank": index + 1})
        for index, candidate in enumerate(sorted(excluded, key=_rank_key))
    ]
    selected = ranked[0] if ranked and not blockers else None
    if selected is not None:
        status: LambdaCatalogCandidateSelectionStatus = (
            "selected_alternative_catalog_candidate"
        )
    elif blockers:
        status = "operator_selection_required"
    else:
        status = "wait_for_live_availability_recommended"
        blockers.append("no_alternative_catalog_candidate")
    return LambdaCatalogCandidateRotationReport(
        candidates_ranked=ranked,
        excluded_candidates=excluded,
        selected_candidate=selected,
        selection_status=status,
        operator_risk_acceptance_required=selected is not None,
        blockers=sorted(set(blockers)),
        warnings=[
            "catalog rotation uses catalog evidence, not live availability",
            "same-shape retry remains excluded by default after capacity errors",
        ],
    )


def build_lambda_catalog_candidate_rotation_from_paths(
    *,
    price_snapshot: str | Path,
    capacity_history: str | Path,
    ssh_key_selection: str | Path,
    max_budget: float = 50.0,
    allow_failed_shape_retry: bool = False,
) -> LambdaCatalogCandidateRotationReport:
    history = load_lambda_capacity_history(capacity_history)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    policy = default_lambda_catalog_candidate_policy(
        allow_operator_override_for_failed_shape=allow_failed_shape_retry,
        max_budget=max_budget,
    )
    return build_lambda_catalog_candidate_rotation(
        price_snapshot=load_price_snapshot(price_snapshot),
        capacity_error_shapes=set(history.shapes_with_capacity_errors),
        ssh_key_selection_passed=ssh.selection_passed,
        policy=policy,
    )


def _estimate(price_per_hour: float | None, hours: float) -> float | None:
    return None if price_per_hour is None else round(price_per_hour * hours, 8)


def _buffered(
    price_per_hour: float | None,
    hours: float,
    multiplier: float,
) -> float | None:
    estimate = _estimate(price_per_hour, hours)
    return None if estimate is None else round(estimate * multiplier, 8)


def _rank_key(candidate: LambdaCatalogRotationCandidate) -> tuple[float, int, str]:
    return (
        candidate.buffered_estimated_30min_cost
        if candidate.buffered_estimated_30min_cost is not None
        else float("inf"),
        candidate.gpus_per_instance if candidate.gpus_per_instance is not None else 999,
        candidate.shape,
    )


def load_lambda_catalog_candidate_rotation(
    path: str | Path,
) -> LambdaCatalogCandidateRotationReport:
    return LambdaCatalogCandidateRotationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_catalog_candidate_rotation(
    path: str | Path,
    report: LambdaCatalogCandidateRotationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
