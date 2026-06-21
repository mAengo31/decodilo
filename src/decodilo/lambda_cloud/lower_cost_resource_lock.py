"""Resource lock for the lower-cost future M039 review path."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_final_state_snapshot import (
    LambdaLowerCostFinalStateSnapshot,
    load_lambda_lower_cost_final_state_snapshot,
)
from decodilo.lambda_cloud.strand_lower_cost_launch_plan import (
    LambdaStrandLowerCostLaunchPlanReport,
    load_lambda_strand_lower_cost_launch_plan_report,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    LambdaExistingSSHKeySelectionReport,
    load_lambda_existing_ssh_key_selection,
)


class LambdaLowerCostResourceLock(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    resource_lock_passed: bool
    region_locked: str | None = None
    shape_locked: str | None = None
    ssh_key_locked: bool
    selected_ssh_key_hash: str | None = None
    terminate_scope_future_owned_only: bool = True
    no_create_delete_resources: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostResourceLock:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost resource lock cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_resource_lock(
    *,
    state_snapshot: LambdaLowerCostFinalStateSnapshot,
    launch_plan: LambdaStrandLowerCostLaunchPlanReport,
    ssh_key_selection: LambdaExistingSSHKeySelectionReport,
) -> LambdaLowerCostResourceLock:
    blockers: list[str] = []
    plan = launch_plan.plan
    if not state_snapshot.snapshot_passed:
        blockers.extend(state_snapshot.blockers or ["state_snapshot_failed"])
    if not launch_plan.plan_passed or plan is None:
        blockers.extend(launch_plan.blockers or ["lower_cost_launch_plan_failed"])
    if not ssh_key_selection.selection_passed:
        blockers.extend(ssh_key_selection.errors or ["existing_ssh_key_selection_failed"])
    if not ssh_key_selection.selected_ssh_key_name_redacted_or_hash:
        blockers.append("selected_ssh_key_hash_missing")
    return LambdaLowerCostResourceLock(
        resource_lock_passed=not blockers,
        region_locked=None if plan is None else plan.region,
        shape_locked=None if plan is None else plan.shape,
        ssh_key_locked=ssh_key_selection.selection_passed,
        selected_ssh_key_hash=ssh_key_selection.selected_ssh_key_name_redacted_or_hash,
        blockers=sorted(set(blockers)),
        warnings=["resource lock allows only future owned-instance termination scope"],
    )


def build_lambda_lower_cost_resource_lock_from_paths(
    *,
    state_snapshot: str | Path,
    launch_plan: str | Path,
    ssh_key_selection: str | Path,
) -> LambdaLowerCostResourceLock:
    return build_lambda_lower_cost_resource_lock(
        state_snapshot=load_lambda_lower_cost_final_state_snapshot(state_snapshot),
        launch_plan=load_lambda_strand_lower_cost_launch_plan_report(launch_plan),
        ssh_key_selection=load_lambda_existing_ssh_key_selection(ssh_key_selection),
    )


def load_lambda_lower_cost_resource_lock(path: str | Path) -> LambdaLowerCostResourceLock:
    return LambdaLowerCostResourceLock.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_resource_lock(
    path: str | Path,
    report: LambdaLowerCostResourceLock,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
