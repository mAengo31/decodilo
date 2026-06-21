"""Execution gate for the capacity-selected M046 launch path."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_history_aware_selector import (
    load_lambda_capacity_history_aware_selector,
)
from decodilo.lambda_cloud.capacity_history_selector_authorization import (
    load_lambda_capacity_history_selector_authorization,
)
from decodilo.lambda_cloud.capacity_history_selector_gate_check import (
    load_lambda_capacity_history_selector_gate_check,
)
from decodilo.lambda_cloud.capacity_selected_cost_risk_review import (
    CAPACITY_SELECTED_CANDIDATE,
    load_lambda_capacity_selected_cost_risk_review,
)
from decodilo.lambda_cloud.capacity_selected_gate_check import (
    load_lambda_capacity_selected_gate_check,
)
from decodilo.lambda_cloud.capacity_selected_m046_authorization import (
    load_lambda_capacity_selected_m046_authorization,
)
from decodilo.lambda_cloud.capacity_selected_operator_approval import (
    load_lambda_capacity_selected_operator_approval,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)


class LambdaCapacitySelectedExecutionGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate_passed: bool
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    selected_region: str | None = None
    quantity: int = 1
    selected_ssh_key_hash: str | None = None
    raw_ssh_key_available_for_request_construction: bool
    strand_payload_compatible: bool
    response_capture_active: bool
    status_before_parse: bool
    effective_launch_timeout_seconds: float | None = None
    effective_terminate_timeout_seconds: float | None = None
    effective_read_only_verification_timeout_seconds: float | None = None
    no_auto_launch_retry: bool
    old_path_fallback_blocked: bool = True
    m039_path_fallback_blocked: bool = True
    capacity_selected_path_used: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaCapacitySelectedExecutionGateCheck:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.no_auto_launch_retry
        ):
            raise ValueError("capacity-selected execution gate cannot enable launch")
        if self.gate_passed and self.blockers:
            raise ValueError("capacity-selected execution gate cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_selected_execution_gate_check_from_paths(
    *,
    m046_authorization: str | Path,
    cost_risk_review: str | Path,
    operator_approval: str | Path,
    capacity_selected_gate_check: str | Path,
    capacity_aware_selector_output: str | Path,
    capacity_aware_selector_authorization: str | Path,
    capacity_aware_selector_gate_check: str | Path,
    ssh_key_selection: str | Path,
    response_loss_controls: str | Path,
) -> LambdaCapacitySelectedExecutionGateCheck:
    auth = load_lambda_capacity_selected_m046_authorization(m046_authorization)
    cost = load_lambda_capacity_selected_cost_risk_review(cost_risk_review)
    approval = load_lambda_capacity_selected_operator_approval(operator_approval)
    review_gate = load_lambda_capacity_selected_gate_check(capacity_selected_gate_check)
    selector = load_lambda_capacity_history_aware_selector(capacity_aware_selector_output)
    selector_auth = load_lambda_capacity_history_selector_authorization(
        capacity_aware_selector_authorization
    )
    selector_gate = load_lambda_capacity_history_selector_gate_check(
        capacity_aware_selector_gate_check
    )
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)

    blockers = [
        *auth.blockers,
        *cost.blockers,
        *approval.blockers,
        *review_gate.blockers,
        *selector.blockers,
        *selector_auth.blockers,
        *selector_gate.blockers,
        *ssh.errors,
        *controls.blockers,
    ]
    candidate = selector.selected_candidate
    raw_key_available = bool(ssh.selected_ssh_key_name_for_payload)
    selected_region = (
        auth.selected_region
        or cost.selected_region
        or (candidate.region if candidate is not None else None)
        or "us-west-1"
    )

    if auth.authorization_status != (
        "authorized_for_future_m046_capacity_selected_launch_review"
    ):
        blockers.append("m046_capacity_selected_authorization_not_ready")
    if not cost.cost_risk_review_passed:
        blockers.append("capacity_selected_cost_risk_review_not_passed")
    if approval.approval_status != (
        "approved_for_future_m046_capacity_selected_launch_review"
    ):
        blockers.append("capacity_selected_operator_approval_not_approved")
    if not review_gate.gate_passed:
        blockers.append("capacity_selected_review_gate_not_passed")
    if selector_auth.authorization_status != (
        "authorized_for_future_capacity_history_selector_review"
    ):
        blockers.append("capacity_history_selector_authorization_not_ready")
    if not selector_gate.gate_passed:
        blockers.append("capacity_history_selector_gate_not_passed")
    if candidate is None:
        blockers.append("capacity_aware_selector_candidate_missing")
    elif candidate.shape != CAPACITY_SELECTED_CANDIDATE:
        blockers.append("capacity_aware_selector_candidate_mismatch")
    if auth.selected_candidate != CAPACITY_SELECTED_CANDIDATE:
        blockers.append("m046_authorization_candidate_mismatch")
    if cost.selected_candidate != CAPACITY_SELECTED_CANDIDATE:
        blockers.append("cost_risk_review_candidate_mismatch")
    if review_gate.selected_candidate != CAPACITY_SELECTED_CANDIDATE:
        blockers.append("capacity_selected_gate_candidate_mismatch")
    if selector_auth.selected_candidate != CAPACITY_SELECTED_CANDIDATE:
        blockers.append("selector_authorization_candidate_mismatch")
    if selector_gate.selected_candidate != CAPACITY_SELECTED_CANDIDATE:
        blockers.append("selector_gate_candidate_mismatch")
    if candidate is not None and candidate.quantity != 1:
        blockers.append("quantity_must_equal_one")
    if not raw_key_available:
        blockers.append("raw_existing_ssh_key_name_missing_from_private_artifact")
    if ssh.raw_public_key_material_present:
        blockers.append("raw_public_key_material_present")
    if not ssh.selection_passed:
        blockers.append("existing_ssh_key_selection_required")
    if not controls.controls_passed:
        blockers.append("response_loss_controls_not_passed")
    if not controls.response_capture_active:
        blockers.append("response_capture_not_active")
    if not controls.status_before_parse:
        blockers.append("status_before_parse_not_enabled")
    if controls.timeout_seconds < 30:
        blockers.append("timeout_seconds_below_30")
    if not controls.no_auto_launch_retry:
        blockers.append("auto_launch_retry_must_be_disabled")
    if not controls.strand_launch_payload_shape_valid:
        blockers.append("strand_launch_payload_shape_invalid")
    if not selected_region:
        blockers.append("selected_region_missing_for_strand_payload")

    expected_hash = auth.selected_ssh_key_hash or review_gate.selected_ssh_key_hash
    for label, value in {
        "capacity_selected_gate": review_gate.selected_ssh_key_hash,
        "selector_authorization": selector_auth.selected_ssh_key_hash,
        "ssh_key_selection": ssh.selected_ssh_key_name_redacted_or_hash,
    }.items():
        if expected_hash and value != expected_hash:
            blockers.append(f"{label}_ssh_key_hash_mismatch")

    warnings = [
        "capacity-selected execution gate is offline/review-only",
        "raw SSH key name is consumed only from the private selection artifact",
        "old M028/M029 fallback is blocked when M046 flags are present",
        "M039 lower-cost fallback is blocked when M046 flags are present",
    ]
    if auth.selected_region is None and cost.selected_region is None and (
        candidate is None or candidate.region is None
    ):
        warnings.append(
            "catalog candidate did not carry a region; execution gate uses us-west-1 "
            "as the Strand payload region"
        )

    return LambdaCapacitySelectedExecutionGateCheck(
        gate_passed=not blockers,
        selected_candidate=auth.selected_candidate,
        selected_candidate_source=auth.selected_candidate_source
        or selector.selected_candidate_source,
        selected_region=selected_region,
        quantity=1 if candidate is None else candidate.quantity,
        selected_ssh_key_hash=expected_hash,
        raw_ssh_key_available_for_request_construction=raw_key_available,
        strand_payload_compatible=bool(
            controls.strand_launch_payload_shape_valid
            and (candidate is None or candidate.strand_payload_compatible)
        ),
        response_capture_active=controls.response_capture_active,
        status_before_parse=controls.status_before_parse,
        effective_launch_timeout_seconds=controls.timeout_seconds,
        effective_terminate_timeout_seconds=controls.timeout_seconds,
        effective_read_only_verification_timeout_seconds=controls.timeout_seconds,
        no_auto_launch_retry=controls.no_auto_launch_retry,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def load_lambda_capacity_selected_execution_gate_check(
    path: str | Path,
) -> LambdaCapacitySelectedExecutionGateCheck:
    return LambdaCapacitySelectedExecutionGateCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_selected_execution_gate_check(
    path: str | Path,
    report: LambdaCapacitySelectedExecutionGateCheck,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
