"""Rank Lambda lifecycle-smoke launch candidates by availability and cost."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_capacity_candidate_extractor import (
    LambdaCapacityCandidate,
    LambdaLiveCapacityCandidateExtractorReport,
    load_lambda_live_capacity_candidate_extractor,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    LambdaExistingSSHKeySelectionReport,
    load_lambda_existing_ssh_key_selection,
)

LambdaAvailabilityFirstSelectionStatus = Literal[
    "selected_live_available",
    "selected_catalog_only_requires_risk_acceptance",
    "selected_catalog_only_risk_accepted",
    "no_candidate",
]


class LambdaAvailabilityFirstRankedCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    rank: int
    shape: str
    quantity: Literal[1] = 1
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    region: str | None = None
    price_per_instance_hour: float | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    live_available: bool
    source: str
    selection_basis: str
    selection_reason: str
    strand_payload_compatible: bool = True
    filesystem_required: bool = False
    existing_ssh_key_required: bool = True
    ssh_usage_allowed: bool = False
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    training_allowed: bool = False
    no_auto_launch_retry: bool = True
    owned_instance_termination_required: bool = True


class LambdaAvailabilityFirstCandidateRankerReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    ranked_candidates: list[LambdaAvailabilityFirstRankedCandidate] = Field(
        default_factory=list
    )
    selected_candidate: LambdaAvailabilityFirstRankedCandidate | None = None
    selection_status: LambdaAvailabilityFirstSelectionStatus
    selected_candidate_reason: str | None = None
    launch_selection_allowed: bool = False
    catalog_only_risk_accepted: bool = False
    approved_shape_count: int | None = None
    operator_risk_acceptance_required: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaAvailabilityFirstCandidateRankerReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("availability-first ranking cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def rank_lambda_availability_first_candidates(
    *,
    candidates: LambdaLiveCapacityCandidateExtractorReport,
    ssh_key_selection: LambdaExistingSSHKeySelectionReport,
    max_budget: float = 50.0,
    approved_shapes: set[str] | None = None,
    catalog_only_risk_accepted: bool = False,
    no_auto_launch_retry: bool = True,
    owned_instance_termination_required: bool = True,
) -> LambdaAvailabilityFirstCandidateRankerReport:
    blockers: list[str] = []
    if not ssh_key_selection.selection_passed:
        blockers.extend(ssh_key_selection.errors or ["existing_ssh_key_selection_failed"])
    if candidates.errors:
        blockers.extend(candidates.errors)
    if not no_auto_launch_retry:
        blockers.append("automatic_launch_retry_must_be_disabled")
    if not owned_instance_termination_required:
        blockers.append("owned_instance_termination_must_be_required")
    merged = _merge_candidates(candidates)
    viable: list[LambdaCapacityCandidate] = []
    for candidate in merged:
        if approved_shapes is not None and candidate.shape not in approved_shapes:
            continue
        if not candidate.strand_payload_compatible or candidate.filesystem_required:
            continue
        if candidate.buffered_estimated_30min_cost is None:
            continue
        if candidate.buffered_estimated_30min_cost >= max_budget:
            continue
        viable.append(candidate)
    if not viable:
        blockers.append("no_viable_availability_first_candidate")
    ranked = [
        LambdaAvailabilityFirstRankedCandidate(
            rank=index + 1,
            shape=candidate.shape,
            gpu_type=candidate.gpu_type,
            gpus_per_instance=candidate.gpus_per_instance,
            region=candidate.region,
            price_per_instance_hour=candidate.price_per_instance_hour,
            estimated_30min_cost=candidate.estimated_30min_cost,
            buffered_estimated_30min_cost=candidate.buffered_estimated_30min_cost,
            live_available=candidate.live_available,
            source=candidate.source,
            selection_basis=(
                "live_available_lowest_buffered_cost_single_gpu_no_filesystem_strand_payload"
                if candidate.live_available
                else "catalog_only_lowest_buffered_cost_single_gpu_no_filesystem_strand_payload"
            ),
            selection_reason=_candidate_reason(candidate),
            strand_payload_compatible=candidate.strand_payload_compatible,
            filesystem_required=candidate.filesystem_required,
            no_auto_launch_retry=no_auto_launch_retry,
            owned_instance_termination_required=owned_instance_termination_required,
        )
        for index, candidate in enumerate(sorted(viable, key=_rank_key))
    ]
    selected = ranked[0] if ranked and not blockers else None
    if selected is None:
        status: LambdaAvailabilityFirstSelectionStatus = "no_candidate"
    elif selected.live_available:
        status = "selected_live_available"
    elif catalog_only_risk_accepted:
        status = "selected_catalog_only_risk_accepted"
    else:
        status = "selected_catalog_only_requires_risk_acceptance"
    launch_selection_allowed = bool(
        selected
        and (selected.live_available or catalog_only_risk_accepted)
        and not blockers
    )
    warnings = [
        "catalog-only selection requires future operator risk acceptance",
        "availability-first ranking is review-only and does not authorize launch",
    ]
    if selected is not None and not selected.live_available and not catalog_only_risk_accepted:
        warnings.append(
            "no live-available candidate exists; catalog-only candidate is not "
            "launchable without explicit operator risk acceptance"
        )
    return LambdaAvailabilityFirstCandidateRankerReport(
        ranked_candidates=ranked,
        selected_candidate=selected,
        selection_status=status,
        selected_candidate_reason=None if selected is None else selected.selection_reason,
        launch_selection_allowed=launch_selection_allowed,
        catalog_only_risk_accepted=catalog_only_risk_accepted,
        approved_shape_count=None if approved_shapes is None else len(approved_shapes),
        operator_risk_acceptance_required=bool(selected and not selected.live_available),
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def rank_lambda_availability_first_candidates_from_paths(
    *,
    candidates: str | Path,
    ssh_key_selection: str | Path,
    max_budget: float = 50.0,
    approved_shapes: set[str] | None = None,
    catalog_only_risk_accepted: bool = False,
    no_auto_launch_retry: bool = True,
    owned_instance_termination_required: bool = True,
) -> LambdaAvailabilityFirstCandidateRankerReport:
    return rank_lambda_availability_first_candidates(
        candidates=load_lambda_live_capacity_candidate_extractor(candidates),
        ssh_key_selection=load_lambda_existing_ssh_key_selection(ssh_key_selection),
        max_budget=max_budget,
        approved_shapes=approved_shapes,
        catalog_only_risk_accepted=catalog_only_risk_accepted,
        no_auto_launch_retry=no_auto_launch_retry,
        owned_instance_termination_required=owned_instance_termination_required,
    )


def _merge_candidates(
    candidates: LambdaLiveCapacityCandidateExtractorReport,
) -> list[LambdaCapacityCandidate]:
    catalog_by_shape = {
        candidate.shape: candidate for candidate in candidates.product_catalog_candidates
    }
    merged: list[LambdaCapacityCandidate] = []
    for live in candidates.live_candidates:
        catalog = catalog_by_shape.get(live.shape)
        merged.append(
            live.model_copy(
                update={
                    "price_per_instance_hour": live.price_per_instance_hour
                    if live.price_per_instance_hour is not None
                    else (None if catalog is None else catalog.price_per_instance_hour),
                    "estimated_30min_cost": live.estimated_30min_cost
                    if live.estimated_30min_cost is not None
                    else (None if catalog is None else catalog.estimated_30min_cost),
                    "buffered_estimated_30min_cost": live.buffered_estimated_30min_cost
                    if live.buffered_estimated_30min_cost is not None
                    else (
                        None
                        if catalog is None
                        else catalog.buffered_estimated_30min_cost
                    ),
                }
            )
        )
    live_shapes = {candidate.shape for candidate in candidates.live_candidates}
    merged.extend(
        candidate
        for candidate in candidates.product_catalog_candidates
        if candidate.shape not in live_shapes
    )
    return merged


def _rank_key(candidate: LambdaCapacityCandidate) -> tuple[int, float, int, int, str]:
    return (
        0 if candidate.live_available else 1,
        candidate.buffered_estimated_30min_cost
        if candidate.buffered_estimated_30min_cost is not None
        else float("inf"),
        candidate.gpus_per_instance if candidate.gpus_per_instance is not None else 999,
        1 if candidate.filesystem_required else 0,
        candidate.shape,
    )


def _candidate_reason(candidate: LambdaCapacityCandidate) -> str:
    availability = (
        "live availability evidence"
        if candidate.live_available
        else "catalog evidence only; explicit risk acceptance required before launch"
    )
    return (
        f"selected by {availability}, buffered_30min_cost="
        f"{candidate.buffered_estimated_30min_cost}, gpus_per_instance="
        f"{candidate.gpus_per_instance}, filesystem_required="
        f"{candidate.filesystem_required}, strand_payload_compatible="
        f"{candidate.strand_payload_compatible}"
    )


def load_lambda_availability_first_candidate_ranker(
    path: str | Path,
) -> LambdaAvailabilityFirstCandidateRankerReport:
    return LambdaAvailabilityFirstCandidateRankerReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_availability_first_candidate_ranker(
    path: str | Path,
    report: LambdaAvailabilityFirstCandidateRankerReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
