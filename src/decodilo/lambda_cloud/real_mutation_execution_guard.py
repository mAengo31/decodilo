"""Execution guard for the disabled Lambda real mutation skeleton."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.mutation_arming_state import LambdaMutationArmingState
from decodilo.lambda_cloud.mutation_budget_lock import LambdaMutationBudgetLock
from decodilo.lambda_cloud.mutation_idempotency_plan import LambdaMutationIdempotencyPlan
from decodilo.lambda_cloud.mutation_resource_scope import LambdaMutationResourceScope
from decodilo.lambda_cloud.real_mutation_feature_flags import LambdaMutationFeatureFlags


class LambdaRealMutationGuardCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    criterion_id: str
    satisfied_for_review: bool = False
    satisfied_for_execution: bool = False
    blocker_for_execution: bool = True
    message: str


class LambdaRealMutationExecutionGuardReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    criteria: list[LambdaRealMutationGuardCriterion]
    review_only_passed: bool
    execution_guard_passed_for_execution: bool = False
    status: Literal["review_only", "blocked_for_execution"] = "blocked_for_execution"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _execution_never_passes(self) -> LambdaRealMutationExecutionGuardReport:
        if (
            self.execution_guard_passed_for_execution
            or self.real_mutation_enabled
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
        ):
            raise ValueError("M024 execution guard cannot pass for execution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRealMutationExecutionGuard(BaseModel):
    model_config = ConfigDict(frozen=True)

    guard_schema_version: int = 1
    feature_flags: LambdaMutationFeatureFlags = Field(
        default_factory=LambdaMutationFeatureFlags
    )
    arming_state: LambdaMutationArmingState = Field(default_factory=LambdaMutationArmingState)
    current_milestone: str = "M024"

    def evaluate(
        self,
        *,
        operation_name: str,
        operation_allowed_by_spec: bool,
        approval_present: bool,
        budget_lock: LambdaMutationBudgetLock | None,
        resource_scope: LambdaMutationResourceScope | None,
        teardown_plan_present: bool,
        termination_policy_present: bool,
        idempotency_plan: LambdaMutationIdempotencyPlan | None,
        kill_switch_present: bool,
        live_read_only_discovery_present: bool,
        no_unmanaged_billable_resources: bool,
        launch_window_policy_present: bool,
    ) -> LambdaRealMutationExecutionGuardReport:
        criteria = [
            _criterion(
                "mutation_feature_flag_disabled",
                not self.feature_flags.real_mutation_transport_executable,
                "mutation feature flags remain disabled",
            ),
            _criterion(
                "arming_state_unarmed",
                not self.arming_state.mutation_armed,
                "mutation arming state is unarmed",
            ),
            _criterion(
                "operation_spec_present",
                operation_allowed_by_spec,
                f"operation spec exists for {operation_name}",
            ),
            _criterion("human_approval_present", approval_present, "approval evidence exists"),
            _criterion("budget_lock_present", budget_lock is not None, "budget lock exists"),
            _criterion("resource_scope_valid", resource_scope is not None, "resource scope exists"),
            _criterion("teardown_plan_present", teardown_plan_present, "teardown plan exists"),
            _criterion(
                "termination_verification_policy_present",
                termination_policy_present,
                "termination verification policy exists",
            ),
            _criterion(
                "idempotency_key_present",
                idempotency_plan is not None,
                "idempotency plan exists",
            ),
            _criterion("kill_switch_present", kill_switch_present, "kill-switch design exists"),
            _criterion(
                "live_read_only_discovery_present",
                live_read_only_discovery_present,
                "live read-only discovery evidence exists",
            ),
            _criterion(
                "no_unmanaged_billable_resources",
                no_unmanaged_billable_resources,
                "no unmanaged billable resources are in scope",
            ),
            _criterion(
                "launch_window_policy_present",
                launch_window_policy_present,
                "launch window policy exists",
            ),
            LambdaRealMutationGuardCriterion(
                criterion_id="current_milestone_forbids_execution",
                satisfied_for_review=True,
                satisfied_for_execution=False,
                blocker_for_execution=True,
                message="M024 forbids real mutation execution",
            ),
        ]
        review_only = all(criterion.satisfied_for_review for criterion in criteria)
        blockers = [
            criterion.criterion_id
            for criterion in criteria
            if not criterion.satisfied_for_review or criterion.blocker_for_execution
        ]
        return LambdaRealMutationExecutionGuardReport(
            criteria=criteria,
            review_only_passed=review_only,
            blockers=blockers,
            warnings=["Guard may pass review-only checks, but execution remains impossible."],
        )


def _criterion(
    criterion_id: str,
    satisfied: bool,
    message: str,
) -> LambdaRealMutationGuardCriterion:
    return LambdaRealMutationGuardCriterion(
        criterion_id=criterion_id,
        satisfied_for_review=satisfied,
        satisfied_for_execution=False,
        blocker_for_execution=not satisfied,
        message=message,
    )


def write_lambda_real_mutation_execution_guard_report(
    path: str | Path,
    report: LambdaRealMutationExecutionGuardReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
