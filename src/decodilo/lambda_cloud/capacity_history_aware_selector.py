"""Capacity-history-aware flexible Lambda selector."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_aware_retry_policy import (
    load_lambda_capacity_aware_retry_policy,
)
from decodilo.lambda_cloud.capacity_history import load_lambda_capacity_history
from decodilo.lambda_cloud.capacity_history_selector_policy import (
    LambdaCapacityHistorySelectorPolicy,
    build_lambda_capacity_history_selector_policy,
)
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.same_shape_capacity_retry_acceptance import (
    LambdaSameShapeCapacityRetryAcceptance,
    load_lambda_same_shape_capacity_retry_acceptance,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot

LambdaCapacityHistoryAwareSelectionStatus = Literal[
    "selected_capacity_history_eligible_candidate",
    "selected_same_shape_retry_with_explicit_acceptance",
    "no_candidate_wait_for_live_availability",
]


class LambdaCapacityHistoryAwareCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    rank: int
    shape: str
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    region: str | None = None
    source: Literal["live_instance_types", "product_catalog"]
    live_available: bool = False
    price_per_instance_hour: float | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    quantity: Literal[1] = 1
    strand_payload_compatible: bool = True
    filesystem_required: bool = False
    recent_capacity_failure: bool = False
    excluded: bool = False
    exclusion_reason: str | None = None
    selection_reason: str | None = None


class LambdaCapacityHistoryAwareSelectorReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    candidates_seen: list[LambdaCapacityHistoryAwareCandidate] = Field(default_factory=list)
    candidates_excluded: list[LambdaCapacityHistoryAwareCandidate] = Field(
        default_factory=list
    )
    exclusion_reasons: dict[str, str] = Field(default_factory=dict)
    selected_candidate: LambdaCapacityHistoryAwareCandidate | None = None
    selected_candidate_source: str | None = None
    selected_candidate_reason: str | None = None
    selection_status: LambdaCapacityHistoryAwareSelectionStatus
    capacity_history_used: bool = True
    same_shape_retry_required: bool = False
    same_shape_retry_acceptance_present: bool = False
    recent_capacity_failure_excluded_candidates: list[str] = Field(default_factory=list)
    recommended_next_step: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCapacityHistoryAwareSelectorReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("capacity-history-aware selector cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_history_aware_selector_from_paths(
    *,
    capacity_history: str | Path,
    capacity_retry_policy: str | Path,
    price_snapshot: str | Path,
    ssh_key_selection: str | Path,
    response_loss_controls: str | Path,
    discovery_report: str | Path | None = None,
    same_shape_retry_acceptance: str | Path | None = None,
    max_budget: float = 50.0,
) -> LambdaCapacityHistoryAwareSelectorReport:
    history = load_lambda_capacity_history(capacity_history)
    retry_policy = load_lambda_capacity_aware_retry_policy(capacity_retry_policy)
    prices = load_price_snapshot(price_snapshot)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    discovery = (
        None
        if discovery_report is None or not Path(discovery_report).exists()
        else load_lambda_live_discovery_report(discovery_report)
    )
    acceptance = (
        None
        if same_shape_retry_acceptance is None
        or not Path(same_shape_retry_acceptance).exists()
        else load_lambda_same_shape_capacity_retry_acceptance(same_shape_retry_acceptance)
    )
    policy = build_lambda_capacity_history_selector_policy(max_budget=max_budget)
    return build_lambda_capacity_history_aware_selector(
        capacity_error_shapes=set(history.shapes_with_capacity_errors),
        retry_policy_same_shape_blocked=retry_policy.same_shape_retry_blocked,
        price_snapshot=prices,
        ssh_key_selection_passed=ssh.selection_passed,
        response_loss_controls_passed=controls.controls_passed
        and controls.no_auto_launch_retry,
        discovery=discovery,
        same_shape_retry_acceptance=acceptance,
        policy=policy,
    )


def build_lambda_capacity_history_aware_selector(
    *,
    capacity_error_shapes: set[str],
    retry_policy_same_shape_blocked: bool,
    price_snapshot: PriceSnapshot,
    ssh_key_selection_passed: bool,
    response_loss_controls_passed: bool,
    discovery: LambdaLiveDiscoveryReport | None = None,
    same_shape_retry_acceptance: LambdaSameShapeCapacityRetryAcceptance | None = None,
    policy: LambdaCapacityHistorySelectorPolicy | None = None,
) -> LambdaCapacityHistoryAwareSelectorReport:
    policy = policy or build_lambda_capacity_history_selector_policy()
    blockers: list[str] = []
    if price_snapshot.is_sample_data:
        blockers.append("sample_price_snapshot_not_allowed")
    if not ssh_key_selection_passed:
        blockers.append("existing_ssh_key_selection_required")
    if not response_loss_controls_passed:
        blockers.append("response_loss_controls_not_passed")
    live_shape_regions = _live_shape_regions(discovery)
    live_shapes = set(live_shape_regions)
    accepted_retry_shape = _accepted_retry_shape(same_shape_retry_acceptance)
    seen: list[LambdaCapacityHistoryAwareCandidate] = []
    included: list[LambdaCapacityHistoryAwareCandidate] = []
    excluded: list[LambdaCapacityHistoryAwareCandidate] = []
    for record in price_snapshot.records:
        if record.provider != "lambda":
            continue
        candidate = _candidate_from_record(
            record,
            policy=policy,
            live_available=record.instance_type in live_shapes,
            live_region=_first_live_region(live_shape_regions.get(record.instance_type, [])),
            recent_capacity_failure=record.instance_type in capacity_error_shapes,
        )
        exclusion_reason = _exclusion_reason(
            candidate,
            policy=policy,
            retry_policy_same_shape_blocked=retry_policy_same_shape_blocked,
            accepted_retry_shape=accepted_retry_shape,
        )
        candidate = candidate.model_copy(
            update={
                "excluded": exclusion_reason is not None,
                "exclusion_reason": exclusion_reason,
            }
        )
        seen.append(candidate)
        if exclusion_reason is None:
            included.append(candidate)
        else:
            excluded.append(candidate)
    included = [
        candidate.model_copy(
            update={"rank": index + 1, "selection_reason": _selection_reason(candidate)}
        )
        for index, candidate in enumerate(sorted(included, key=_rank_key))
    ]
    excluded = [
        candidate.model_copy(update={"rank": index + 1})
        for index, candidate in enumerate(sorted(excluded, key=_rank_key))
    ]
    selected = included[0] if included and not blockers else None
    if selected is None:
        status: LambdaCapacityHistoryAwareSelectionStatus = (
            "no_candidate_wait_for_live_availability"
        )
        if not blockers:
            blockers.append("no_capacity_history_eligible_candidate")
    elif selected.shape == accepted_retry_shape and selected.recent_capacity_failure:
        status = "selected_same_shape_retry_with_explicit_acceptance"
    else:
        status = "selected_capacity_history_eligible_candidate"
    recent_excluded = [
        candidate.shape
        for candidate in excluded
        if candidate.exclusion_reason == "recent_capacity_error_excluded"
    ]
    return LambdaCapacityHistoryAwareSelectorReport(
        candidates_seen=seen,
        candidates_excluded=excluded,
        exclusion_reasons={
            candidate.shape: candidate.exclusion_reason or ""
            for candidate in excluded
            if candidate.exclusion_reason
        },
        selected_candidate=selected,
        selected_candidate_source=None if selected is None else selected.source,
        selected_candidate_reason=None if selected is None else selected.selection_reason,
        selection_status=status,
        same_shape_retry_required=bool(recent_excluded),
        same_shape_retry_acceptance_present=accepted_retry_shape is not None,
        recent_capacity_failure_excluded_candidates=recent_excluded,
        recommended_next_step=(
            "wait_for_live_availability" if selected is None else "future_review_only"
        ),
        blockers=sorted(set(blockers)),
        warnings=[
            "capacity-history-aware selector is review-only",
            "recent capacity-failed shapes are excluded unless fresh live availability exists",
        ],
    )


def _candidate_from_record(
    record: SnapshotPriceRecord,
    *,
    policy: LambdaCapacityHistorySelectorPolicy,
    live_available: bool,
    live_region: str | None = None,
    recent_capacity_failure: bool,
) -> LambdaCapacityHistoryAwareCandidate:
    estimate = None if record.price_per_instance_hour is None else round(
        record.price_per_instance_hour * policy.max_runtime_minutes / 60.0,
        8,
    )
    buffered = None if estimate is None else round(estimate * 1.15, 8)
    return LambdaCapacityHistoryAwareCandidate(
        rank=0,
        shape=record.instance_type,
        gpu_type=record.gpu_type,
        gpus_per_instance=record.gpus_per_instance,
        region=live_region or record.region,
        source="live_instance_types" if live_available else "product_catalog",
        live_available=live_available,
        price_per_instance_hour=record.price_per_instance_hour,
        estimated_30min_cost=estimate,
        buffered_estimated_30min_cost=buffered,
        recent_capacity_failure=recent_capacity_failure,
    )


def _exclusion_reason(
    candidate: LambdaCapacityHistoryAwareCandidate,
    *,
    policy: LambdaCapacityHistorySelectorPolicy,
    retry_policy_same_shape_blocked: bool,
    accepted_retry_shape: str | None,
) -> str | None:
    if candidate.buffered_estimated_30min_cost is None:
        return "missing_price"
    if candidate.buffered_estimated_30min_cost >= policy.max_budget:
        return "buffered_cost_not_below_budget"
    if candidate.filesystem_required:
        return "filesystem_requirement_not_allowed"
    if not candidate.strand_payload_compatible:
        return "strand_payload_not_compatible"
    if (
        candidate.recent_capacity_failure
        and policy.exclude_recent_capacity_failures
        and retry_policy_same_shape_blocked
        and not candidate.live_available
        and candidate.shape != accepted_retry_shape
    ):
        return "recent_capacity_error_excluded"
    return None


def _live_shape_regions(discovery: LambdaLiveDiscoveryReport | None) -> dict[str, list[str]]:
    if discovery is None:
        return {}
    result: dict[str, list[str]] = {}
    for item in discovery.instance_types:
        name = item.name or item.instance_type_id
        if not name:
            continue
        result[name] = list(item.regions)
    return result


def _first_live_region(regions: list[str]) -> str | None:
    return sorted(set(regions))[0] if regions else None


def _accepted_retry_shape(
    acceptance: LambdaSameShapeCapacityRetryAcceptance | None,
) -> str | None:
    if (
        acceptance is not None
        and acceptance.acceptance_status
        == "accepted_for_future_same_shape_capacity_retry_review"
    ):
        return acceptance.shape
    return None


def _rank_key(candidate: LambdaCapacityHistoryAwareCandidate) -> tuple[int, float, int, int, str]:
    return (
        0 if candidate.live_available else 1,
        candidate.buffered_estimated_30min_cost
        if candidate.buffered_estimated_30min_cost is not None
        else float("inf"),
        candidate.gpus_per_instance if candidate.gpus_per_instance is not None else 999,
        1 if candidate.filesystem_required else 0,
        candidate.shape,
    )


def _selection_reason(candidate: LambdaCapacityHistoryAwareCandidate) -> str:
    basis = "fresh live availability" if candidate.live_available else "catalog evidence"
    return (
        f"selected by {basis}, excluding recent capacity-failed shapes; "
        f"buffered_30min_cost={candidate.buffered_estimated_30min_cost}, "
        f"gpus_per_instance={candidate.gpus_per_instance}, "
        f"strand_payload_compatible={candidate.strand_payload_compatible}"
    )


def load_lambda_capacity_history_aware_selector(
    path: str | Path,
) -> LambdaCapacityHistoryAwareSelectorReport:
    return LambdaCapacityHistoryAwareSelectorReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_history_aware_selector(
    path: str | Path,
    report: LambdaCapacityHistoryAwareSelectorReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
