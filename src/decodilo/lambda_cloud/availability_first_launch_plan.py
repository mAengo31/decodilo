"""Future-only availability-first Lambda launch plan."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.availability_first_candidate_ranker import (
    LambdaAvailabilityFirstCandidateRankerReport,
    load_lambda_availability_first_candidate_ranker,
)
from decodilo.lambda_cloud.strand_cli_request_shapes import validate_strand_launch_payload
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    LambdaExistingSSHKeySelectionReport,
    load_lambda_existing_ssh_key_selection,
)

LambdaRegionSelectionMode = Literal[
    "fixed_region",
    "provider_auto_select",
    "live_candidate_region",
]


class LambdaAvailabilityFirstLaunchPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    selected_shape: str
    selected_region: str | None = None
    provider_auto_select: bool = False
    region_selection_mode: LambdaRegionSelectionMode
    selected_ssh_key_hash: str | None = None
    ssh_key_names_private_available: bool = False
    quantity: Literal[1] = 1
    strand_payload_compatible: bool
    filesystem_names: list[str] = Field(default_factory=list)
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    training_allowed: bool = False
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    availability_basis: str
    risk_acceptance_required: bool
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaAvailabilityFirstLaunchPlan:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.setup_scripts_allowed
            or self.cloud_init_allowed
            or self.training_allowed
        ):
            raise ValueError("availability-first launch plan cannot enable launch")
        return self


class LambdaAvailabilityFirstLaunchPlanReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    plan: LambdaAvailabilityFirstLaunchPlan | None = None
    plan_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaAvailabilityFirstLaunchPlanReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("availability-first launch plan report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_availability_first_launch_plan(
    *,
    rank: LambdaAvailabilityFirstCandidateRankerReport,
    ssh_key_selection: LambdaExistingSSHKeySelectionReport | None = None,
    default_region: str = "us-west-1",
    provider_auto_select_supported: bool = False,
) -> LambdaAvailabilityFirstLaunchPlanReport:
    blockers: list[str] = []
    candidate = rank.selected_candidate
    if candidate is None:
        blockers.extend(rank.blockers or ["availability_first_candidate_not_selected"])
    if rank.blockers:
        blockers.extend(rank.blockers)
    selected_hash = None
    key_private_available = False
    if ssh_key_selection is not None:
        selected_hash = ssh_key_selection.selected_ssh_key_name_redacted_or_hash
        key_private_available = bool(ssh_key_selection.selected_ssh_key_name_for_payload)
        if not ssh_key_selection.selection_passed:
            blockers.extend(ssh_key_selection.errors or ["ssh_key_selection_failed"])
    region = None if candidate is None else candidate.region
    mode: LambdaRegionSelectionMode = "fixed_region"
    if region:
        mode = "live_candidate_region" if candidate and candidate.live_available else "fixed_region"
    elif provider_auto_select_supported:
        mode = "provider_auto_select"
    else:
        region = default_region
        mode = "fixed_region"
    plan = None
    if candidate is not None and not blockers:
        strand_ok = _strand_payload_ok(
            shape=candidate.shape,
            region=region,
            provider_auto_select=mode == "provider_auto_select",
            ssh_key_name=(
                ssh_key_selection.selected_ssh_key_name_for_payload
                if ssh_key_selection is not None
                else "existing-key"
            ),
        )
        if not strand_ok:
            blockers.append("availability_first_plan_not_strand_payload_compatible")
        else:
            plan = LambdaAvailabilityFirstLaunchPlan(
                selected_shape=candidate.shape,
                selected_region=region,
                provider_auto_select=mode == "provider_auto_select",
                region_selection_mode=mode,
                selected_ssh_key_hash=selected_hash,
                ssh_key_names_private_available=key_private_available,
                strand_payload_compatible=True,
                estimated_30min_cost=candidate.estimated_30min_cost,
                buffered_estimated_30min_cost=candidate.buffered_estimated_30min_cost,
                availability_basis=candidate.selection_basis,
                risk_acceptance_required=rank.operator_risk_acceptance_required,
            )
    return LambdaAvailabilityFirstLaunchPlanReport(
        plan=plan if not blockers else None,
        plan_passed=not blockers,
        blockers=sorted(set(blockers)),
        warnings=[
            "availability-first launch plan is future-review only",
            "catalog-only availability basis requires future operator risk acceptance",
        ],
    )


def build_lambda_availability_first_launch_plan_from_paths(
    *,
    rank: str | Path,
    ssh_key_selection: str | Path | None = None,
    default_region: str = "us-west-1",
    provider_auto_select_supported: bool = False,
) -> LambdaAvailabilityFirstLaunchPlanReport:
    return build_lambda_availability_first_launch_plan(
        rank=load_lambda_availability_first_candidate_ranker(rank),
        ssh_key_selection=(
            None
            if ssh_key_selection is None
            else load_lambda_existing_ssh_key_selection(ssh_key_selection)
        ),
        default_region=default_region,
        provider_auto_select_supported=provider_auto_select_supported,
    )


def _strand_payload_ok(
    *,
    shape: str,
    region: str | None,
    provider_auto_select: bool,
    ssh_key_name: str | None,
) -> bool:
    if not ssh_key_name:
        return False
    payload: dict[str, object] = {
        "instance_type_name": shape,
        "ssh_key_names": [ssh_key_name],
        "quantity": 1,
    }
    if not provider_auto_select:
        if not region:
            return False
        payload["region_name"] = region
    try:
        validate_strand_launch_payload(payload)
    except Exception:  # noqa: BLE001
        return False
    return True


def load_lambda_availability_first_launch_plan(
    path: str | Path,
) -> LambdaAvailabilityFirstLaunchPlanReport:
    return LambdaAvailabilityFirstLaunchPlanReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_availability_first_launch_plan(
    path: str | Path,
    report: LambdaAvailabilityFirstLaunchPlanReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
