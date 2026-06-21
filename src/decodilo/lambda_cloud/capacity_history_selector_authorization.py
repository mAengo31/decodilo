"""Future-only authorization for capacity-history-aware selector output."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_history_aware_selector import (
    load_lambda_capacity_history_aware_selector,
)
from decodilo.lambda_cloud.same_shape_capacity_retry_acceptance import (
    load_lambda_same_shape_capacity_retry_acceptance,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)

LambdaCapacityHistorySelectorAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_capacity_history_selector_review",
]


class LambdaCapacityHistorySelectorArtifactRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str


class LambdaCapacityHistorySelectorAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selector_output_ref: LambdaCapacityHistorySelectorArtifactRef
    ssh_key_selection_ref: LambdaCapacityHistorySelectorArtifactRef
    response_loss_controls_ref: LambdaCapacityHistorySelectorArtifactRef
    same_shape_retry_acceptance_ref: LambdaCapacityHistorySelectorArtifactRef | None = None
    authorization_status: LambdaCapacityHistorySelectorAuthorizationStatus
    authorization_source: Literal["capacity_history_aware_selector"] = (
        "capacity_history_aware_selector"
    )
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    selected_candidate_has_recent_capacity_failure: bool = False
    same_shape_retry_acceptance_required: bool = False
    same_shape_retry_acceptance_present: bool = False
    selected_ssh_key_hash: str | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    launch_authorized_for_next_milestone: bool = False
    launch_authorized_now: bool = False
    no_auto_launch_retry: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaCapacityHistorySelectorAuthorization:
        if (
            self.launch_authorized_now
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.no_auto_launch_retry
        ):
            raise ValueError("capacity-history selector authorization cannot launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_history_selector_authorization_from_paths(
    *,
    selector_output: str | Path,
    ssh_key_selection: str | Path,
    response_loss_controls: str | Path,
    same_shape_retry_acceptance: str | Path | None = None,
    max_budget: float = 50.0,
) -> LambdaCapacityHistorySelectorAuthorization:
    selector = load_lambda_capacity_history_aware_selector(selector_output)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    acceptance = (
        None
        if same_shape_retry_acceptance is None
        or not Path(same_shape_retry_acceptance).exists()
        else load_lambda_same_shape_capacity_retry_acceptance(same_shape_retry_acceptance)
    )
    blockers = [*selector.blockers, *ssh.errors, *controls.blockers]
    candidate = selector.selected_candidate
    acceptance_present = (
        acceptance is not None
        and acceptance.acceptance_status
        == "accepted_for_future_same_shape_capacity_retry_review"
    )
    if candidate is None:
        blockers.append("capacity_history_selector_candidate_missing")
    else:
        if candidate.quantity != 1:
            blockers.append("quantity_must_equal_1")
        if candidate.buffered_estimated_30min_cost is None:
            blockers.append("buffered_30min_cost_missing")
        elif candidate.buffered_estimated_30min_cost >= max_budget:
            blockers.append("buffered_30min_cost_over_budget")
        if candidate.filesystem_required:
            blockers.append("filesystem_requirement_not_allowed")
        if not candidate.strand_payload_compatible:
            blockers.append("strand_payload_not_compatible")
        if candidate.recent_capacity_failure and not (
            candidate.live_available or acceptance_present
        ):
            blockers.append("same_shape_capacity_retry_acceptance_required")
    if not ssh.selection_passed or ssh.selected_ssh_key_name_redacted_or_hash is None:
        blockers.append("existing_ssh_key_selection_required")
    if not controls.controls_passed:
        blockers.append("response_loss_controls_not_passed")
    if not controls.no_auto_launch_retry:
        blockers.append("auto_launch_retry_must_be_disabled")
    passed = not blockers
    return LambdaCapacityHistorySelectorAuthorization(
        selector_output_ref=_ref(selector_output),
        ssh_key_selection_ref=_ref(ssh_key_selection),
        response_loss_controls_ref=_ref(response_loss_controls),
        same_shape_retry_acceptance_ref=(
            None if same_shape_retry_acceptance is None else _ref(same_shape_retry_acceptance)
        ),
        authorization_status=(
            "authorized_for_future_capacity_history_selector_review"
            if passed
            else "not_authorized"
        ),
        selected_candidate=None if candidate is None else candidate.shape,
        selected_candidate_source=None if candidate is None else candidate.source,
        selected_candidate_has_recent_capacity_failure=(
            False if candidate is None else candidate.recent_capacity_failure
        ),
        same_shape_retry_acceptance_required=bool(
            candidate is not None
            and candidate.recent_capacity_failure
            and not candidate.live_available
        ),
        same_shape_retry_acceptance_present=acceptance_present,
        selected_ssh_key_hash=ssh.selected_ssh_key_name_redacted_or_hash if passed else None,
        estimated_30min_cost=None if candidate is None else candidate.estimated_30min_cost,
        buffered_estimated_30min_cost=(
            None if candidate is None else candidate.buffered_estimated_30min_cost
        ),
        launch_authorized_for_next_milestone=passed,
        no_auto_launch_retry=controls.no_auto_launch_retry,
        blockers=sorted(set(blockers)),
        warnings=[
            "authorization is future-review only",
            "selected candidate comes from capacity-history-aware selector output",
        ],
    )


def _ref(path: str | Path) -> LambdaCapacityHistorySelectorArtifactRef:
    target = Path(path)
    return LambdaCapacityHistorySelectorArtifactRef(
        path=str(target),
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    )


def load_lambda_capacity_history_selector_authorization(
    path: str | Path,
) -> LambdaCapacityHistorySelectorAuthorization:
    return LambdaCapacityHistorySelectorAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_history_selector_authorization(
    path: str | Path,
    report: LambdaCapacityHistorySelectorAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
