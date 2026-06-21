"""M029 one-run arming gate for the first real Lambda launch attempt."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.final_budget_lock import (
    LambdaFinalBudgetLock,
    load_lambda_final_budget_lock,
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
from decodilo.lambda_cloud.m028_decision_record import (
    LambdaM028DecisionRecord,
    load_lambda_m028_decision_record,
)
from decodilo.lambda_cloud.m028_report import LambdaM028Report, load_lambda_m028_report
from decodilo.lambda_cloud.m029_launch_authorization import (
    LambdaM029AuthorizationPackage,
    load_lambda_m029_authorization_package,
)

CONFIRM_BILLABLE_ACTION = (
    "I understand this may create a billable Lambda instance and must be terminated"
)
CONFIRM_TERMINATE_REQUIRED = (
    "I understand this run must terminate the owned instance and verify termination"
)


class LambdaM029ArmingToken(BaseModel):
    model_config = ConfigDict(frozen=True)

    token_schema_version: int = 1
    token_id: str
    run_id: str
    allowed_operations: list[str] = Field(
        default_factory=lambda: [
            "launch_one_instance",
            "read_only_verify_instance",
            "terminate_owned_instance",
            "read_only_verify_terminated",
        ]
    )
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    max_instances: int = 1
    arming_succeeded: bool = False
    used: bool = False
    fake_server_mode: bool = False
    real_lambda_api_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _strict_scope(self) -> LambdaM029ArmingToken:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M029 arming token cannot set launch flags true")
        if self.max_budget > 50 or self.max_runtime_minutes > 30 or self.max_instances != 1:
            raise ValueError("M029 arming token exceeds first-launch limits")
        forbidden = {
            "restart",
            "create_ssh_key",
            "delete_ssh_key",
            "create_filesystem",
            "delete_filesystem",
        }
        if forbidden.intersection(self.allowed_operations):
            raise ValueError("M029 arming token includes forbidden operation")
        return self

    def require_unused(self) -> None:
        if self.used:
            raise ValueError("M029 arming token has already been used")
        if not self.arming_succeeded or self.blockers:
            raise ValueError("M029 arming token is not valid")

    def mark_used(self) -> LambdaM029ArmingToken:
        self.require_unused()
        return self.model_copy(update={"used": True})

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM029ArmingReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    run_id: str
    arming_passed: bool
    token: LambdaM029ArmingToken | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def arm_lambda_m029_launch(
    *,
    run_id: str,
    execute_real_launch: bool,
    confirm_billable_action: str,
    confirm_terminate_required: str,
    m028_decision: str | Path | LambdaM028DecisionRecord,
    m029_authorization: str | Path | LambdaM029AuthorizationPackage,
    budget_lock: str | Path | LambdaFinalBudgetLock,
    resource_lock: str | Path | LambdaFinalResourceLock,
    launch_window_lock: str | Path | LambdaLaunchWindowLock,
    operator_confirmation: str | Path | LambdaFinalOperatorConfirmation,
    state_snapshot: str | Path | LambdaFinalPrelaunchStateSnapshot,
    teardown_plan: str | Path | LambdaFinalTeardownVerificationPlan,
    emergency_stop_present: bool,
    idempotency_key: str,
    fake_server_mode: bool = False,
) -> LambdaM029ArmingReport:
    blockers: list[str] = []
    decision = _load_decision(m028_decision)
    authorization = _load_authorization(m029_authorization)
    budget = _load_budget(budget_lock)
    resource = _load_resource(resource_lock)
    window = _load_window(launch_window_lock)
    operator = _load_operator(operator_confirmation)
    snapshot = _load_snapshot(state_snapshot)
    teardown = _load_teardown(teardown_plan)

    if not execute_real_launch:
        blockers.append("missing --execute-real-launch")
    if confirm_billable_action != CONFIRM_BILLABLE_ACTION:
        blockers.append("missing exact billable-action confirmation")
    if confirm_terminate_required != CONFIRM_TERMINATE_REQUIRED:
        blockers.append("missing exact terminate-required confirmation")
    if decision.status != "authorized_for_m029_one_instance_launch_attempt":
        blockers.append("M028 decision did not authorize M029 attempt")
    if not authorization.package_passed:
        blockers.extend(authorization.blockers or ["M029 authorization package failed"])
    if not budget.budget_lock_passed or budget.max_budget > 50:
        blockers.extend(budget.blockers or ["budget lock failed"])
    if not resource.resource_lock_passed:
        blockers.extend(resource.blockers or ["resource lock failed"])
    if not window.launch_window_valid:
        blockers.extend(window.blockers or ["launch window invalid"])
    blockers.extend(_window_time_blockers(window))
    if not evaluate_lambda_final_operator_confirmation(operator).confirmation_passed:
        blockers.append("operator confirmation incomplete")
    if not snapshot.snapshot_passed:
        blockers.extend(snapshot.blockers or ["state snapshot failed"])
    if snapshot.unmanaged_billable_count:
        blockers.append("unmanaged billable resources present")
    if not teardown.plan_passed:
        blockers.extend(teardown.blockers or ["teardown verification plan failed"])
    if not emergency_stop_present:
        blockers.append("emergency stop evidence missing")
    if not idempotency_key:
        blockers.append("idempotency key missing")

    token = _build_token(
        run_id=run_id,
        authorization=authorization,
        arming_succeeded=not blockers,
        blockers=blockers,
        fake_server_mode=fake_server_mode,
    )
    return LambdaM029ArmingReport(
        run_id=run_id,
        arming_passed=not blockers,
        token=token,
        blockers=blockers,
        warnings=[
            "M029 arming is scoped to one launch request and owned-instance termination."
        ],
    )


def arm_lambda_m029_from_package(
    *,
    run_id: str,
    execute_real_launch: bool,
    confirm_billable_action: str,
    confirm_terminate_required: str,
    m028_report: str | Path | LambdaM028Report,
    m029_authorization: str | Path | LambdaM029AuthorizationPackage,
    emergency_stop_present: bool,
    idempotency_key: str,
    fake_server_mode: bool = False,
) -> LambdaM029ArmingReport:
    blockers: list[str] = []
    report = _load_m028_report(m028_report)
    authorization = _load_authorization(m029_authorization)
    if not execute_real_launch:
        blockers.append("missing --execute-real-launch")
    if confirm_billable_action != CONFIRM_BILLABLE_ACTION:
        blockers.append("missing exact billable-action confirmation")
    if confirm_terminate_required != CONFIRM_TERMINATE_REQUIRED:
        blockers.append("missing exact terminate-required confirmation")
    if not report.report_passed:
        blockers.extend(report.blockers or ["M028 report failed"])
    if report.decision_record.status != "authorized_for_m029_one_instance_launch_attempt":
        blockers.append("M028 decision did not authorize M029 attempt")
    if not authorization.package_passed:
        blockers.extend(authorization.blockers or ["M029 authorization package failed"])
    launch = authorization.launch_authorization
    if launch.max_budget > 50 or launch.max_runtime_minutes > 30 or launch.max_instances != 1:
        blockers.append("M029 authorization exceeds hard limits")
    if not emergency_stop_present:
        blockers.append("emergency stop evidence missing")
    if not idempotency_key:
        blockers.append("idempotency key missing")
    token = _build_token(
        run_id=run_id,
        authorization=authorization,
        arming_succeeded=not blockers,
        blockers=blockers,
        fake_server_mode=fake_server_mode,
    )
    return LambdaM029ArmingReport(
        run_id=run_id,
        arming_passed=not blockers,
        token=token,
        blockers=blockers,
        warnings=[
            "M029 package arming is scoped to one launch request and owned termination."
        ],
    )


def _build_token(
    *,
    run_id: str,
    authorization: LambdaM029AuthorizationPackage,
    arming_succeeded: bool,
    blockers: list[str],
    fake_server_mode: bool,
) -> LambdaM029ArmingToken:
    material = "|".join(
        [
            run_id,
            authorization.launch_authorization.authorization_id,
            str(fake_server_mode),
        ]
    )
    return LambdaM029ArmingToken(
        token_id="m029-arm-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16],
        run_id=run_id,
        max_budget=authorization.launch_authorization.max_budget,
        max_runtime_minutes=authorization.launch_authorization.max_runtime_minutes,
        max_instances=authorization.launch_authorization.max_instances,
        arming_succeeded=arming_succeeded,
        fake_server_mode=fake_server_mode,
        real_lambda_api_allowed=arming_succeeded and not fake_server_mode,
        blockers=blockers,
    )


def _window_time_blockers(window: LambdaLaunchWindowLock) -> list[str]:
    now = datetime.now(timezone.utc)
    blockers: list[str] = []
    if window.valid_after_utc and _parse_utc(window.valid_after_utc) > now:
        blockers.append("launch window has not opened")
    if window.valid_until_utc and _parse_utc(window.valid_until_utc) <= now:
        blockers.append("launch window has expired")
    return blockers


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _load_decision(value: str | Path | LambdaM028DecisionRecord) -> LambdaM028DecisionRecord:
    if isinstance(value, LambdaM028DecisionRecord):
        return value
    return load_lambda_m028_decision_record(value)


def _load_m028_report(value: str | Path | LambdaM028Report) -> LambdaM028Report:
    if isinstance(value, LambdaM028Report):
        return value
    return load_lambda_m028_report(value)


def _load_authorization(
    value: str | Path | LambdaM029AuthorizationPackage,
) -> LambdaM029AuthorizationPackage:
    if isinstance(value, LambdaM029AuthorizationPackage):
        return value
    return load_lambda_m029_authorization_package(value)


def _load_budget(value: str | Path | LambdaFinalBudgetLock) -> LambdaFinalBudgetLock:
    if isinstance(value, LambdaFinalBudgetLock):
        return value
    return load_lambda_final_budget_lock(value)


def _load_resource(value: str | Path | LambdaFinalResourceLock) -> LambdaFinalResourceLock:
    if isinstance(value, LambdaFinalResourceLock):
        return value
    return load_lambda_final_resource_lock(value)


def _load_window(value: str | Path | LambdaLaunchWindowLock) -> LambdaLaunchWindowLock:
    if isinstance(value, LambdaLaunchWindowLock):
        return value
    return load_lambda_launch_window_lock(value)


def _load_operator(
    value: str | Path | LambdaFinalOperatorConfirmation,
) -> LambdaFinalOperatorConfirmation:
    if isinstance(value, LambdaFinalOperatorConfirmation):
        return value
    return load_lambda_final_operator_confirmation(value)


def _load_snapshot(
    value: str | Path | LambdaFinalPrelaunchStateSnapshot,
) -> LambdaFinalPrelaunchStateSnapshot:
    if isinstance(value, LambdaFinalPrelaunchStateSnapshot):
        return value
    return load_lambda_final_prelaunch_state_snapshot(value)


def _load_teardown(
    value: str | Path | LambdaFinalTeardownVerificationPlan,
) -> LambdaFinalTeardownVerificationPlan:
    if isinstance(value, LambdaFinalTeardownVerificationPlan):
        return value
    return load_lambda_final_teardown_verification_plan(value)


def load_lambda_m029_arming_report(path: str | Path) -> LambdaM029ArmingReport:
    return LambdaM029ArmingReport.model_validate_json(Path(path).read_text("utf-8"))


def write_lambda_m029_arming_report(path: str | Path, report: LambdaM029ArmingReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
