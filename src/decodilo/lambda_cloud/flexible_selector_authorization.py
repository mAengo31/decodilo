"""Future-only authorization driven by flexible availability-first selector output."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.availability_first_candidate_ranker import (
    load_lambda_availability_first_candidate_ranker,
)
from decodilo.lambda_cloud.flexible_selector_operator_approval import (
    load_lambda_flexible_selector_operator_approval,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import load_price_snapshot

LambdaFlexibleSelectorAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_flexible_selector_launch_review",
]


class LambdaFlexibleSelectorArtifactRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str


class LambdaFlexibleSelectorAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selector_output_ref: LambdaFlexibleSelectorArtifactRef
    operator_approval_ref: LambdaFlexibleSelectorArtifactRef
    ssh_key_selection_ref: LambdaFlexibleSelectorArtifactRef
    response_loss_controls_ref: LambdaFlexibleSelectorArtifactRef
    price_snapshot_ref: LambdaFlexibleSelectorArtifactRef | None = None
    authorization_status: LambdaFlexibleSelectorAuthorizationStatus
    authorization_source: Literal["flexible_selector_output"] = (
        "flexible_selector_output"
    )
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    selected_candidate_reason: str | None = None
    selected_region: str | None = None
    selected_ssh_key_hash: str | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    launch_authorized_for_next_milestone: bool = False
    launch_authorized_now: bool = False
    selector_launch_selection_allowed: bool = False
    catalog_only_risk_accepted: bool = False
    no_auto_launch_retry: bool = True
    fixed_shape_path_used: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaFlexibleSelectorAuthorization:
        if (
            self.launch_authorized_now
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.fixed_shape_path_used
            or not self.no_auto_launch_retry
        ):
            raise ValueError("flexible-selector authorization cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_flexible_selector_authorization_from_paths(
    *,
    selector_output: str | Path,
    operator_approval: str | Path,
    ssh_key_selection: str | Path,
    response_loss_controls: str | Path,
    price_snapshot: str | Path | None = None,
    max_budget: float = 50.0,
) -> LambdaFlexibleSelectorAuthorization:
    selector = load_lambda_availability_first_candidate_ranker(selector_output)
    approval = load_lambda_flexible_selector_operator_approval(operator_approval)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    blockers = [
        *selector.blockers,
        *approval.blockers,
        *ssh.errors,
        *controls.blockers,
    ]
    warnings = [
        "authorization is future-review only",
        "selector output is the sole selected-shape source",
    ]
    if price_snapshot is None:
        warnings.append("price snapshot not supplied; relying on selector price evidence")
    else:
        snapshot = load_price_snapshot(price_snapshot)
        if snapshot.is_sample_data:
            blockers.append("sample_price_snapshot_not_allowed")
    candidate = selector.selected_candidate
    if candidate is None:
        blockers.append("selector_candidate_missing")
    else:
        if not selector.launch_selection_allowed:
            blockers.append("selector_launch_selection_not_allowed")
        if candidate.quantity != 1:
            blockers.append("quantity_must_equal_1")
        if candidate.buffered_estimated_30min_cost is None:
            blockers.append("buffered_30min_cost_missing")
        elif candidate.buffered_estimated_30min_cost >= max_budget:
            blockers.append("buffered_30min_cost_over_budget")
        if not candidate.strand_payload_compatible:
            blockers.append("strand_payload_not_compatible")
        if candidate.filesystem_required:
            blockers.append("filesystem_requirement_not_allowed")
        if not candidate.no_auto_launch_retry:
            blockers.append("auto_launch_retry_must_be_disabled")
        if not candidate.owned_instance_termination_required:
            blockers.append("owned_instance_termination_required")
        if not candidate.live_available and not selector.catalog_only_risk_accepted:
            blockers.append("catalog_only_risk_acceptance_required")
    if approval.approval_status != "approved_for_future_flexible_selector_launch_review":
        blockers.append("flexible_selector_operator_approval_required")
    if not ssh.selection_passed or ssh.selected_ssh_key_name_redacted_or_hash is None:
        blockers.append("existing_ssh_key_selection_required")
    if not controls.controls_passed:
        blockers.append("response_loss_controls_not_passed")
    if not controls.no_auto_launch_retry:
        blockers.append("auto_launch_retry_must_be_disabled")
    passed = not blockers
    return LambdaFlexibleSelectorAuthorization(
        selector_output_ref=_ref(selector_output),
        operator_approval_ref=_ref(operator_approval),
        ssh_key_selection_ref=_ref(ssh_key_selection),
        response_loss_controls_ref=_ref(response_loss_controls),
        price_snapshot_ref=None if price_snapshot is None else _ref(price_snapshot),
        authorization_status=(
            "authorized_for_future_flexible_selector_launch_review"
            if passed
            else "not_authorized"
        ),
        selected_candidate=None if candidate is None else candidate.shape,
        selected_candidate_source=None if candidate is None else candidate.source,
        selected_candidate_reason=selector.selected_candidate_reason,
        selected_region=None if candidate is None else candidate.region,
        selected_ssh_key_hash=ssh.selected_ssh_key_name_redacted_or_hash if passed else None,
        estimated_30min_cost=None if candidate is None else candidate.estimated_30min_cost,
        buffered_estimated_30min_cost=(
            None if candidate is None else candidate.buffered_estimated_30min_cost
        ),
        launch_authorized_for_next_milestone=passed,
        selector_launch_selection_allowed=selector.launch_selection_allowed,
        catalog_only_risk_accepted=selector.catalog_only_risk_accepted,
        no_auto_launch_retry=controls.no_auto_launch_retry,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
    )


def _ref(path: str | Path) -> LambdaFlexibleSelectorArtifactRef:
    target = Path(path)
    return LambdaFlexibleSelectorArtifactRef(
        path=str(target),
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    )


def load_lambda_flexible_selector_authorization(
    path: str | Path,
) -> LambdaFlexibleSelectorAuthorization:
    return LambdaFlexibleSelectorAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_flexible_selector_authorization(
    path: str | Path,
    report: LambdaFlexibleSelectorAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
