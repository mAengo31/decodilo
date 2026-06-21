"""M027 minimal mutation executor limited to local fake server execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from decodilo.lambda_cloud.fake_server_failure_modes import (
    LambdaMinimalFakeFailureMode,
)
from decodilo.lambda_cloud.minimal_mutation_execution_context import (
    LambdaMinimalMutationExecutionContext,
)
from decodilo.lambda_cloud.minimal_mutation_execution_policy import (
    LambdaMinimalMutationPolicyReport,
    evaluate_minimal_mutation_execution_policy,
)
from decodilo.lambda_cloud.minimal_mutation_fake_transport import (
    LambdaMinimalMutationFakeTransport,
)
from decodilo.lambda_cloud.minimal_mutation_request import (
    LambdaMinimalLaunchOneInstanceRequest,
    LambdaMinimalTerminateOwnedInstanceRequest,
)
from decodilo.lambda_cloud.minimal_mutation_response_parser import (
    parse_minimal_mutation_response,
)
from decodilo.lambda_cloud.minimal_mutation_result import (
    LambdaMinimalLaunchResult,
    LambdaMinimalTerminateResult,
)
from decodilo.lambda_cloud.minimal_mutation_safety_checks import (
    LambdaMinimalMutationSafetyCheckReport,
    run_minimal_mutation_safety_checks,
)


@dataclass
class LambdaMinimalMutationExecutor:
    context: LambdaMinimalMutationExecutionContext
    transport: LambdaMinimalMutationFakeTransport = field(
        default_factory=LambdaMinimalMutationFakeTransport
    )
    m027_authorization_present: bool = True
    operation_spec_present: bool = True
    budget_lock_present: bool = True
    idempotency_plan_present: bool = True
    resource_scope_present: bool = True
    teardown_plan_present: bool = True
    termination_policy_present: bool = True
    no_unmanaged_billable_resources: bool = True
    audit_events: list[dict] = field(default_factory=list)

    def policy_report(self) -> LambdaMinimalMutationPolicyReport:
        return evaluate_minimal_mutation_execution_policy(
            context=self.context,
            m027_authorization_present=self.m027_authorization_present,
            operation_spec_present=self.operation_spec_present,
            budget_lock_present=self.budget_lock_present,
            idempotency_plan_present=self.idempotency_plan_present,
            resource_scope_present=self.resource_scope_present,
            teardown_plan_present=self.teardown_plan_present,
            termination_policy_present=self.termination_policy_present,
            no_unmanaged_billable_resources=self.no_unmanaged_billable_resources,
        )

    def safety_report(self) -> LambdaMinimalMutationSafetyCheckReport:
        return run_minimal_mutation_safety_checks(self.context)

    def execute_launch(
        self,
        request: LambdaMinimalLaunchOneInstanceRequest,
        *,
        failure_mode: LambdaMinimalFakeFailureMode = "none",
    ) -> LambdaMinimalLaunchResult:
        self._require_fake_execution()
        payload = self.transport.launch_one_instance(request, failure_mode=failure_mode)
        result = parse_minimal_mutation_response(payload)
        if not isinstance(result, LambdaMinimalLaunchResult):
            raise ValueError("launch response parsed as non-launch result")
        self._record("launch_one_instance", request.idempotency_key, result.instance_id)
        return result

    def execute_terminate(
        self,
        request: LambdaMinimalTerminateOwnedInstanceRequest,
        *,
        failure_mode: LambdaMinimalFakeFailureMode = "none",
    ) -> LambdaMinimalTerminateResult:
        self._require_fake_execution()
        payload = self.transport.terminate_owned_instance(request, failure_mode=failure_mode)
        result = parse_minimal_mutation_response(payload)
        if not isinstance(result, LambdaMinimalTerminateResult):
            raise ValueError("terminate response parsed as non-terminate result")
        self._record("terminate_owned_instance", request.idempotency_key, result.instance_id)
        return result

    def _require_fake_execution(self) -> None:
        policy = self.policy_report()
        safety = self.safety_report()
        if not policy.fake_execution_allowed:
            raise ValueError("minimal mutation policy blocked fake execution")
        if not safety.safety_checks_passed:
            raise ValueError("minimal mutation safety checks blocked fake execution")

    def _record(self, operation: str, idempotency_key: str, instance_id: str) -> None:
        self.audit_events.append(
            {
                "operation": operation,
                "idempotency_key": idempotency_key,
                "instance_id": instance_id,
                "fake_server_only": True,
                "real_lambda_api_used": False,
                "billable_action_performed": False,
            }
        )
