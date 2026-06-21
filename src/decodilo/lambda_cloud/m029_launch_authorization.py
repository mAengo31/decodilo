"""M028 one-time M029 launch authorization package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.final_budget_lock import (
    LambdaFinalBudgetLock,
    load_lambda_final_budget_lock,
)
from decodilo.lambda_cloud.final_no_mutation_audit import (
    LambdaFinalNoMutationAudit,
    load_lambda_final_no_mutation_audit,
)
from decodilo.lambda_cloud.final_operator_confirmation import (
    LambdaFinalOperatorConfirmation,
    evaluate_lambda_final_operator_confirmation,
    load_lambda_final_operator_confirmation,
)
from decodilo.lambda_cloud.final_prelaunch_state_snapshot import (
    LambdaFinalPrelaunchStateSnapshot,
    load_lambda_final_prelaunch_state_snapshot,
)
from decodilo.lambda_cloud.final_resource_lock import (
    LambdaFinalResourceLock,
    load_lambda_final_resource_lock,
)
from decodilo.lambda_cloud.final_teardown_verification_plan import (
    LambdaFinalTeardownVerificationPlan,
    load_lambda_final_teardown_verification_plan,
)
from decodilo.lambda_cloud.launch_window_lock import (
    LambdaLaunchWindowLock,
    load_lambda_launch_window_lock,
)
from decodilo.lambda_cloud.m029_termination_authorization import (
    LambdaM029TerminationAuthorization,
    build_lambda_m029_termination_authorization,
)


class LambdaM029LaunchAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_id: str
    authorized_for: str = "M029_one_instance_launch_attempt"
    authorized_operations: list[str] = Field(default_factory=list)
    forbidden_operations: list[str] = Field(default_factory=list)
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    max_instances: int = 1
    planned_instance_type: str
    planned_region: str
    image_ref: str | None = None
    ssh_key_ref: str | None = None
    filesystem_refs: list[str] = Field(default_factory=list)
    idempotency_plan_hash: str
    budget_lock_hash: str
    resource_lock_hash: str
    launch_window_lock_hash: str
    teardown_plan_hash: str
    operator_confirmation_hash: str
    launch_authorized_for_next_milestone: bool = True
    launch_authorized_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaM029LaunchAuthorization:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M029 launch authorization cannot enable launch in M028")
        if self.launch_authorized_now:
            raise ValueError("M028 cannot authorize launch now")
        if self.max_budget > 50 or self.max_runtime_minutes > 30 or self.max_instances != 1:
            raise ValueError("M029 launch authorization exceeds first-launch limits")
        forbidden = {
            "restart",
            "create_ssh_key",
            "delete_ssh_key",
            "create_filesystem",
            "delete_filesystem",
        }
        if forbidden.intersection(self.authorized_operations):
            raise ValueError("forbidden operation included in M029 launch authorization")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM029AuthorizationPackage(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    package_id: str = "lambda-m029-authorization-package-m028"
    launch_authorization: LambdaM029LaunchAuthorization
    termination_authorization: LambdaM029TerminationAuthorization
    package_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaM029AuthorizationPackage:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M029 authorization package cannot enable launch in M028")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m029_authorization_package(
    *,
    state_snapshot: str | Path | LambdaFinalPrelaunchStateSnapshot | None = None,
    budget_lock: str | Path | LambdaFinalBudgetLock,
    resource_lock: str | Path | LambdaFinalResourceLock,
    launch_window_lock: str | Path | LambdaLaunchWindowLock,
    teardown_plan: str | Path | LambdaFinalTeardownVerificationPlan,
    operator_confirmation: str | Path | LambdaFinalOperatorConfirmation,
    no_mutation_audit: str | Path | LambdaFinalNoMutationAudit | None = None,
) -> LambdaM029AuthorizationPackage:
    snapshot = _load_snapshot(state_snapshot)
    budget, budget_ref = _load_budget(budget_lock)
    resource, resource_ref = _load_resource(resource_lock)
    window, window_ref = _load_window(launch_window_lock)
    teardown, teardown_ref = _load_teardown(teardown_plan)
    operator, operator_ref = _load_operator(operator_confirmation)
    no_mutation = _load_no_mutation(no_mutation_audit)
    operator_report = evaluate_lambda_final_operator_confirmation(operator)
    blockers: list[str] = []
    if snapshot is None:
        blockers.append("final state snapshot missing")
    elif not snapshot.snapshot_passed:
        blockers.extend(snapshot.blockers)
    if not budget.budget_lock_passed:
        blockers.extend(budget.blockers)
    if not resource.resource_lock_passed:
        blockers.extend(resource.blockers)
    if not window.launch_window_valid:
        blockers.extend(window.blockers)
    if not teardown.plan_passed:
        blockers.extend(teardown.blockers)
    if not operator_report.confirmation_passed:
        blockers.extend(operator_report.blockers)
    if no_mutation is None:
        blockers.append("final no-mutation audit missing")
    elif not no_mutation.audit_passed:
        blockers.extend(no_mutation.blockers)
    auth_id_material = "|".join(
        [
            budget.lock_hash,
            resource.lock_hash,
            window.lock_hash,
            _hash_ref(teardown_ref),
            _hash_ref(operator_ref),
        ]
    )
    authorization_id = (
        "lambda-m029-launch-"
        + hashlib.sha256(auth_id_material.encode("utf-8")).hexdigest()[:16]
    )
    launch = LambdaM029LaunchAuthorization(
        authorization_id=authorization_id,
        authorized_operations=[
            "launch_one_instance",
            "read_only_verify_instance",
            "terminate_owned_instance",
            "read_only_verify_terminated",
        ],
        forbidden_operations=[
            "restart",
            "create/delete SSH key",
            "create/delete filesystem",
            "multi-instance launch",
            "SSH",
            "setup scripts",
            "training",
        ],
        max_budget=budget.max_budget,
        max_runtime_minutes=budget.max_runtime_minutes,
        max_instances=budget.max_instances,
        planned_instance_type=resource.planned_instance_type,
        planned_region=resource.planned_region,
        image_ref=resource.image_ref,
        ssh_key_ref=resource.ssh_key_ref,
        filesystem_refs=resource.filesystem_refs,
        idempotency_plan_hash="required-in-m029",
        budget_lock_hash=budget.lock_hash,
        resource_lock_hash=resource.lock_hash,
        launch_window_lock_hash=window.lock_hash,
        teardown_plan_hash=_hash_ref(teardown_ref),
        operator_confirmation_hash=_hash_ref(operator_ref),
        launch_authorized_for_next_milestone=not blockers,
        blockers=blockers,
        warnings=["Authorization is for the next milestone only; M028 remains non-launchable."],
    )
    termination = build_lambda_m029_termination_authorization()
    return LambdaM029AuthorizationPackage(
        launch_authorization=launch,
        termination_authorization=termination,
        package_passed=not blockers,
        blockers=blockers,
        warnings=[*launch.warnings],
    )


def _load_budget(value: str | Path | LambdaFinalBudgetLock) -> tuple[LambdaFinalBudgetLock, str]:
    if isinstance(value, LambdaFinalBudgetLock):
        return value, "<in-memory>"
    return load_lambda_final_budget_lock(value), str(value)


def _load_snapshot(
    value: str | Path | LambdaFinalPrelaunchStateSnapshot | None,
) -> LambdaFinalPrelaunchStateSnapshot | None:
    if value is None or isinstance(value, LambdaFinalPrelaunchStateSnapshot):
        return value
    return load_lambda_final_prelaunch_state_snapshot(value)


def _load_resource(
    value: str | Path | LambdaFinalResourceLock,
) -> tuple[LambdaFinalResourceLock, str]:
    if isinstance(value, LambdaFinalResourceLock):
        return value, "<in-memory>"
    return load_lambda_final_resource_lock(value), str(value)


def _load_window(value: str | Path | LambdaLaunchWindowLock) -> tuple[LambdaLaunchWindowLock, str]:
    if isinstance(value, LambdaLaunchWindowLock):
        return value, "<in-memory>"
    return load_lambda_launch_window_lock(value), str(value)


def _load_teardown(
    value: str | Path | LambdaFinalTeardownVerificationPlan,
) -> tuple[LambdaFinalTeardownVerificationPlan, str]:
    if isinstance(value, LambdaFinalTeardownVerificationPlan):
        return value, "<in-memory>"
    return load_lambda_final_teardown_verification_plan(value), str(value)


def _load_operator(
    value: str | Path | LambdaFinalOperatorConfirmation,
) -> tuple[LambdaFinalOperatorConfirmation, str]:
    if isinstance(value, LambdaFinalOperatorConfirmation):
        return value, "<in-memory>"
    return load_lambda_final_operator_confirmation(value), str(value)


def _load_no_mutation(
    value: str | Path | LambdaFinalNoMutationAudit | None,
) -> LambdaFinalNoMutationAudit | None:
    if value is None or isinstance(value, LambdaFinalNoMutationAudit):
        return value
    return load_lambda_final_no_mutation_audit(value)


def _hash_ref(value: str) -> str:
    if value == "<in-memory>":
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
    path = Path(value)
    if path.exists():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_lambda_m029_authorization_package(path: str | Path) -> LambdaM029AuthorizationPackage:
    return LambdaM029AuthorizationPackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m029_authorization_package(
    path: str | Path,
    package: LambdaM029AuthorizationPackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.to_json(), encoding="utf-8")
