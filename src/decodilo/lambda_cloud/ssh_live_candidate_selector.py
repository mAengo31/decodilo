"""Select live-available Lambda candidates for future SSH connectivity retries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.ssh_capacity_history import load_lambda_ssh_capacity_history
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import load_price_snapshot

BUFFER_MULTIPLIER = 1.15

LambdaSSHLiveCandidateSelectionStatus = Literal[
    "selected_live_candidate",
    "no_candidate_wait_for_availability",
]


class LambdaSSHLiveCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    rank: int
    candidate: str
    region: str
    gpu_type: str | None = None
    gpus_per_instance: int
    price_per_instance_hour: float
    price_evidence_source: str
    estimated_30min_cost: float
    buffered_estimated_30min_cost: float
    selected_candidate_source: str = "live_readonly_instance_types"
    recent_capacity_rejection_for_candidate_region: bool = False
    strand_payload_compatible: bool = True
    existing_ssh_key_required: bool = True
    quantity: Literal[1] = 1
    filesystem_required: bool = False
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    training_allowed: bool = False


class LambdaSSHLiveCandidateSelectionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selection_status: LambdaSSHLiveCandidateSelectionStatus
    ranked_candidates: list[LambdaSSHLiveCandidate] = Field(default_factory=list)
    selected_candidate: str | None = None
    selected_region: str | None = None
    selected_candidate_source: str | None = None
    selected_candidate_reason: str | None = None
    selected_ssh_key_hash: str | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    max_budget: float
    price_snapshot_is_sample: bool
    live_discovery_required_endpoint_success: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHLiveCandidateSelectionReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("SSH live candidate selection cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_live_candidate_selection_from_paths(
    *,
    discovery_report: str | Path,
    price_snapshot: str | Path,
    ssh_key_selection: str | Path,
    capacity_history: str | Path,
    max_budget: float,
) -> LambdaSSHLiveCandidateSelectionReport:
    discovery = load_lambda_live_discovery_report(discovery_report)
    snapshot = load_price_snapshot(price_snapshot)
    ssh_selection = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    history = load_lambda_ssh_capacity_history(capacity_history)
    blockers: list[str] = []
    warnings: list[str] = [
        "selection is future-review only and performs no launch",
        "candidate must be revalidated immediately before any future real run",
    ]
    if not discovery.required_endpoint_success:
        blockers.append("live_discovery_required_endpoint_failed")
    if not ssh_selection.selection_passed:
        blockers.extend(ssh_selection.errors or ["ssh_key_selection_failed"])
    if snapshot.is_sample_data:
        warnings.append("catalog price snapshot is sample; live provider prices may still qualify")
    price_by_shape = {
        record.instance_type: record.price_per_instance_hour for record in snapshot.records
    }
    rejected_pairs = set(history.candidates_with_capacity_rejection)
    candidates: list[LambdaSSHLiveCandidate] = []
    for instance_type in discovery.instance_types:
        if instance_type.gpus <= 0 or not instance_type.regions:
            continue
        price, source = _resolve_price(
            instance_type.name,
            instance_type.price_per_hour,
            price_by_shape,
        )
        if price is None:
            continue
        estimated = price * 0.5
        buffered = estimated * BUFFER_MULTIPLIER
        if buffered >= max_budget:
            continue
        for region in sorted(instance_type.regions):
            pair = f"{instance_type.name}/{region}"
            candidates.append(
                LambdaSSHLiveCandidate(
                    rank=0,
                    candidate=instance_type.name,
                    region=region,
                    gpu_type=instance_type.gpu_type,
                    gpus_per_instance=instance_type.gpus,
                    price_per_instance_hour=price,
                    price_evidence_source=source,
                    estimated_30min_cost=estimated,
                    buffered_estimated_30min_cost=buffered,
                    recent_capacity_rejection_for_candidate_region=pair in rejected_pairs,
                )
            )
    ranked = [
        candidate.model_copy(update={"rank": index + 1})
        for index, candidate in enumerate(sorted(candidates, key=_rank_key))
    ]
    selected = ranked[0] if ranked and not blockers else None
    if selected is None:
        blockers.append("no_live_ssh_retry_candidate_under_budget")
    if any(
        candidate.price_evidence_source == "live_readonly_instance_types"
        for candidate in ranked
    ):
        warnings.append(
            "some live candidates use provider read-only instance-type price because "
            "the catalog snapshot lacks that shape"
        )
    return LambdaSSHLiveCandidateSelectionReport(
        selection_status=(
            "selected_live_candidate"
            if selected is not None
            else "no_candidate_wait_for_availability"
        ),
        ranked_candidates=ranked,
        selected_candidate=None if selected is None else selected.candidate,
        selected_region=None if selected is None else selected.region,
        selected_candidate_source=(
            None if selected is None else selected.selected_candidate_source
        ),
        selected_candidate_reason=(
            None
            if selected is None
            else "cheapest live-available safe candidate for SSH connectivity validation"
        ),
        selected_ssh_key_hash=ssh_selection.selected_ssh_key_name_redacted_or_hash,
        estimated_30min_cost=None if selected is None else selected.estimated_30min_cost,
        buffered_estimated_30min_cost=(
            None if selected is None else selected.buffered_estimated_30min_cost
        ),
        max_budget=max_budget,
        price_snapshot_is_sample=snapshot.is_sample_data,
        live_discovery_required_endpoint_success=discovery.required_endpoint_success,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def _resolve_price(
    shape: str,
    live_price: float | None,
    price_by_shape: dict[str, float],
) -> tuple[float | None, str]:
    if shape in price_by_shape:
        return price_by_shape[shape], "price_snapshot_real_catalog"
    if live_price is not None:
        return live_price, "live_readonly_instance_types"
    return None, "missing"


def _rank_key(candidate: LambdaSSHLiveCandidate) -> tuple[bool, float, bool, str, str]:
    return (
        candidate.recent_capacity_rejection_for_candidate_region,
        candidate.buffered_estimated_30min_cost,
        candidate.gpus_per_instance != 1,
        candidate.candidate,
        candidate.region,
    )


def load_lambda_ssh_live_candidate_selection(
    path: str | Path,
) -> LambdaSSHLiveCandidateSelectionReport:
    return LambdaSSHLiveCandidateSelectionReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_live_candidate_selection(
    path: str | Path,
    report: LambdaSSHLiveCandidateSelectionReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
