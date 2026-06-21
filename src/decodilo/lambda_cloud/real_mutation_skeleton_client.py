"""Disabled real Lambda mutation skeleton client."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.disabled_real_mutation_transport import (
    DisabledLambdaRealMutationTransport,
)
from decodilo.lambda_cloud.mutation_arming_state import LambdaMutationArmingState
from decodilo.lambda_cloud.real_mutation_execution_guard import (
    LambdaRealMutationExecutionGuard,
    LambdaRealMutationExecutionGuardReport,
)
from decodilo.lambda_cloud.real_mutation_feature_flags import LambdaMutationFeatureFlags
from decodilo.lambda_cloud.real_mutation_request_builder import (
    LambdaRealMutationRequestBuilder,
    LambdaRealMutationRequestBuildResult,
)


class LambdaRealMutationSkeletonClient(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    transport: DisabledLambdaRealMutationTransport = Field(
        default_factory=DisabledLambdaRealMutationTransport
    )
    request_builder: LambdaRealMutationRequestBuilder = Field(
        default_factory=LambdaRealMutationRequestBuilder
    )
    execution_guard: LambdaRealMutationExecutionGuard = Field(
        default_factory=LambdaRealMutationExecutionGuard
    )
    feature_flags: LambdaMutationFeatureFlags = Field(default_factory=LambdaMutationFeatureFlags)
    arming_state: LambdaMutationArmingState = Field(default_factory=LambdaMutationArmingState)

    def prepare_launch_one_instance(
        self,
        *,
        operation_spec: str | Path,
        budget_lock: str | Path,
        idempotency_plan: str | Path,
        resource_scope: str | Path,
    ) -> LambdaRealMutationRequestBuildResult:
        return self.request_builder.build_review_plan(
            operation_name="launch_one_instance",
            operation_spec=operation_spec,
            budget_lock=budget_lock,
            idempotency_plan=idempotency_plan,
            resource_scope=resource_scope,
        )

    def prepare_terminate_owned_instance(
        self,
        *,
        operation_spec: str | Path,
        budget_lock: str | Path,
        idempotency_plan: str | Path,
        resource_scope: str | Path,
    ) -> LambdaRealMutationRequestBuildResult:
        return self.request_builder.build_review_plan(
            operation_name="terminate_owned_instance",
            operation_spec=operation_spec,
            budget_lock=budget_lock,
            idempotency_plan=idempotency_plan,
            resource_scope=resource_scope,
        )

    def launch_one_instance(self, *args: object, **kwargs: object) -> None:
        self.transport.launch_one_instance()

    def terminate_owned_instance(self, *args: object, **kwargs: object) -> None:
        self.transport.terminate_owned_instance()

    def evaluate_guard_for_review(self) -> LambdaRealMutationExecutionGuardReport:
        return self.execution_guard.evaluate(
            operation_name="launch_one_instance",
            operation_allowed_by_spec=True,
            approval_present=True,
            budget_lock=object(),  # type: ignore[arg-type]
            resource_scope=object(),  # type: ignore[arg-type]
            teardown_plan_present=True,
            termination_policy_present=True,
            idempotency_plan=object(),  # type: ignore[arg-type]
            kill_switch_present=True,
            live_read_only_discovery_present=True,
            no_unmanaged_billable_resources=True,
            launch_window_policy_present=True,
        )
