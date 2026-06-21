"""Execution gate for the future lower-cost M039 Lambda run path."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_budget_lock import (
    LambdaLowerCostBudgetLock,
    load_lambda_lower_cost_budget_lock,
)
from decodilo.lambda_cloud.lower_cost_canonical_readiness import (
    LambdaLowerCostCanonicalReadinessReport,
    load_lambda_lower_cost_canonical_readiness,
)
from decodilo.lambda_cloud.lower_cost_final_state_snapshot import (
    LambdaLowerCostFinalStateSnapshot,
    load_lambda_lower_cost_final_state_snapshot,
)
from decodilo.lambda_cloud.lower_cost_launch_window_lock import (
    LambdaLowerCostLaunchWindowLock,
    load_lambda_lower_cost_launch_window_lock,
)
from decodilo.lambda_cloud.lower_cost_m039_authorization import (
    LambdaLowerCostM039Authorization,
    load_lambda_lower_cost_m039_authorization,
)
from decodilo.lambda_cloud.lower_cost_resource_lock import (
    LambdaLowerCostResourceLock,
    load_lambda_lower_cost_resource_lock,
)
from decodilo.lambda_cloud.strand_lower_cost_launch_plan import (
    LambdaStrandLowerCostLaunchPlanReport,
    load_lambda_strand_lower_cost_launch_plan_report,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    LambdaStrandResponseLossControlCheck,
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    LambdaExistingSSHKeySelectionReport,
    load_lambda_existing_ssh_key_selection,
)


class LambdaLowerCostExecutionGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate_passed: bool
    selected_shape: str
    selected_region: str
    selected_ssh_key_hash: str | None = None
    raw_ssh_key_available_for_request_construction: bool
    strand_payload_compatible: bool
    response_capture_active: bool
    status_before_parse: bool
    effective_launch_timeout_seconds: float | None = None
    effective_terminate_timeout_seconds: float | None = None
    effective_read_only_verification_timeout_seconds: float | None = None
    no_auto_launch_retry: bool
    lower_cost_path_used: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostExecutionGateCheck:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost execution gate cannot enable launch")
        if self.gate_passed and self.blockers:
            raise ValueError("lower-cost execution gate cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_execution_gate_check(
    *,
    m039_authorization: LambdaLowerCostM039Authorization,
    canonical_readiness: LambdaLowerCostCanonicalReadinessReport,
    state_snapshot: LambdaLowerCostFinalStateSnapshot,
    budget_lock: LambdaLowerCostBudgetLock,
    resource_lock: LambdaLowerCostResourceLock,
    launch_window_lock: LambdaLowerCostLaunchWindowLock,
    launch_plan: LambdaStrandLowerCostLaunchPlanReport,
    ssh_key_selection: LambdaExistingSSHKeySelectionReport,
    response_loss_controls: LambdaStrandResponseLossControlCheck,
) -> LambdaLowerCostExecutionGateCheck:
    blockers: list[str] = []
    plan = launch_plan.plan
    raw_key = ssh_key_selection.selected_ssh_key_name_for_payload
    raw_key_available = bool(raw_key)

    if (
        m039_authorization.authorization_status
        != "authorized_for_future_m039_lower_cost_launch_attempt"
    ):
        blockers.extend(m039_authorization.blockers or ["m039_authorization_not_passed"])
    if not canonical_readiness.readiness_passed:
        blockers.extend(canonical_readiness.blockers or ["canonical_readiness_failed"])
    if not state_snapshot.snapshot_passed:
        blockers.extend(state_snapshot.blockers or ["state_snapshot_failed"])
    if not budget_lock.budget_lock_passed:
        blockers.extend(budget_lock.blockers or ["budget_lock_failed"])
    if not resource_lock.resource_lock_passed:
        blockers.extend(resource_lock.blockers or ["resource_lock_failed"])
    if not launch_window_lock.launch_window_lock_passed:
        blockers.extend(launch_window_lock.blockers or ["launch_window_lock_failed"])
    if not launch_plan.plan_passed or plan is None:
        blockers.extend(launch_plan.blockers or ["lower_cost_launch_plan_failed"])
    if not ssh_key_selection.selection_passed:
        blockers.extend(ssh_key_selection.errors or ["existing_ssh_key_selection_failed"])
    if ssh_key_selection.raw_public_key_material_present:
        blockers.append("raw_public_key_material_present")
    if not raw_key_available:
        blockers.append("raw_existing_ssh_key_name_missing_from_private_artifact")
    if not response_loss_controls.controls_passed:
        blockers.extend(response_loss_controls.blockers or ["response_loss_controls_failed"])

    if canonical_readiness.shape != "gpu_1x_h100_pcie":
        blockers.append("selected_shape_must_be_gpu_1x_h100_pcie")
    if state_snapshot.selected_shape != "gpu_1x_h100_pcie":
        blockers.append("state_snapshot_shape_mismatch")
    if resource_lock.shape_locked != "gpu_1x_h100_pcie":
        blockers.append("resource_lock_shape_mismatch")
    if plan is not None:
        if plan.shape != "gpu_1x_h100_pcie":
            blockers.append("launch_plan_shape_mismatch")
        if plan.instance_type_name != "gpu_1x_h100_pcie":
            blockers.append("launch_plan_instance_type_mismatch")
        if plan.quantity != 1:
            blockers.append("quantity_must_equal_one")
        if plan.region != "us-west-1" or plan.region_name != "us-west-1":
            blockers.append("region_must_equal_us_west_1")
        if raw_key and raw_key not in plan.ssh_key_names:
            blockers.append("private_ssh_key_name_not_used_by_launch_plan")
        if plan.file_system_names:
            blockers.append("filesystem_attachment_not_approved")
        if (
            plan.ssh_allowed
            or plan.setup_scripts_allowed
            or plan.cloud_init_allowed
            or plan.training_allowed
        ):
            blockers.append("ssh_setup_cloud_init_or_training_enabled")

    expected_hash = canonical_readiness.selected_ssh_key_hash
    for label, value in {
        "state_snapshot": state_snapshot.selected_ssh_key_hash,
        "resource_lock": resource_lock.selected_ssh_key_hash,
        "m039_authorization": m039_authorization.selected_ssh_key_hash,
        "ssh_key_selection": ssh_key_selection.selected_ssh_key_name_redacted_or_hash,
    }.items():
        if expected_hash and value != expected_hash:
            blockers.append(f"{label}_ssh_key_hash_mismatch")

    return LambdaLowerCostExecutionGateCheck(
        gate_passed=not blockers,
        selected_shape=canonical_readiness.shape,
        selected_region=canonical_readiness.region,
        selected_ssh_key_hash=canonical_readiness.selected_ssh_key_hash,
        raw_ssh_key_available_for_request_construction=raw_key_available,
        strand_payload_compatible=canonical_readiness.strand_payload_compatible
        and bool(plan is not None and launch_plan.plan_passed),
        response_capture_active=response_loss_controls.response_capture_active,
        status_before_parse=response_loss_controls.status_before_parse,
        effective_launch_timeout_seconds=response_loss_controls.timeout_seconds,
        effective_terminate_timeout_seconds=response_loss_controls.timeout_seconds,
        effective_read_only_verification_timeout_seconds=response_loss_controls.timeout_seconds,
        no_auto_launch_retry=response_loss_controls.no_auto_launch_retry,
        blockers=sorted(set(blockers)),
        warnings=[
            "lower-cost execution gate is offline/review-only",
            "raw SSH key name is consumed only from the private selection artifact",
        ],
    )


def build_lambda_lower_cost_execution_gate_check_from_paths(
    *,
    m039_authorization: str | Path,
    canonical_readiness: str | Path,
    state_snapshot: str | Path,
    budget_lock: str | Path,
    resource_lock: str | Path,
    launch_window_lock: str | Path,
    launch_plan: str | Path,
    ssh_key_selection: str | Path,
    response_loss_controls: str | Path,
) -> LambdaLowerCostExecutionGateCheck:
    return build_lambda_lower_cost_execution_gate_check(
        m039_authorization=load_lambda_lower_cost_m039_authorization(
            m039_authorization
        ),
        canonical_readiness=load_lambda_lower_cost_canonical_readiness(
            canonical_readiness
        ),
        state_snapshot=load_lambda_lower_cost_final_state_snapshot(state_snapshot),
        budget_lock=load_lambda_lower_cost_budget_lock(budget_lock),
        resource_lock=load_lambda_lower_cost_resource_lock(resource_lock),
        launch_window_lock=load_lambda_lower_cost_launch_window_lock(
            launch_window_lock
        ),
        launch_plan=load_lambda_strand_lower_cost_launch_plan_report(launch_plan),
        ssh_key_selection=load_lambda_existing_ssh_key_selection(ssh_key_selection),
        response_loss_controls=load_lambda_strand_response_loss_control_check(
            response_loss_controls
        ),
    )


def load_lambda_lower_cost_execution_gate_check(
    path: str | Path,
) -> LambdaLowerCostExecutionGateCheck:
    return LambdaLowerCostExecutionGateCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_execution_gate_check(
    path: str | Path,
    report: LambdaLowerCostExecutionGateCheck,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
