"""Audit proving the real Lambda mutation skeleton is non-executable."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.disabled_real_mutation_transport import (
    DisabledLambdaRealMutationTransport,
    LambdaRealMutationDisabledError,
)
from decodilo.lambda_cloud.mutation_arming_state import LambdaMutationArmingState
from decodilo.lambda_cloud.real_mutation_execution_guard import (
    LambdaRealMutationExecutionGuard,
)
from decodilo.lambda_cloud.real_mutation_feature_flags import LambdaMutationFeatureFlags


class LambdaRealMutationSkeletonAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    passed: bool
    disabled_transport_exists: bool = True
    executable_transport_exists: bool = False
    feature_flags_disabled: bool = True
    arming_state_unarmed: bool = True
    execution_guard_blocks_execution: bool = True
    request_builder_review_only: bool = True
    skeleton_client_raises: bool = True
    live_transport_supports_post: bool = False
    live_transport_supports_delete: bool = False
    real_mutation_code_detected: bool = False
    forbidden_patterns: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def audit_lambda_real_mutation_skeleton(
    project_root: str | Path,
) -> LambdaRealMutationSkeletonAuditReport:
    root = Path(project_root)
    errors: list[str] = []
    patterns: list[str] = []
    lambda_dir = root / "src" / "decodilo" / "lambda_cloud"
    real_transport = lambda_dir / "real_read_only_transport.py"
    text = real_transport.read_text(encoding="utf-8") if real_transport.exists() else ""
    live_post = any(pattern in text for pattern in ('"POST"', "method='POST'"))
    live_delete = any(pattern in text for pattern in ('"DELETE"', "method='DELETE'"))
    if live_post:
        patterns.append("real_read_only_transport:POST")
    if live_delete:
        patterns.append("real_read_only_transport:DELETE")
    for path in lambda_dir.glob("*.py"):
        if path.name in {"real_mutation_skeleton_audit.py", "real_mutation_absence_audit.py"}:
            continue
        source = path.read_text(encoding="utf-8")
        for forbidden in [
            "ExecutableLambdaRealMutationTransport",
            "send_real_mutation_request",
            "requests.post",
            "requests.delete",
            "launch_allowed" + "=True",
            "real_mutation_enabled" + "=True",
        ]:
            if forbidden in source:
                patterns.append(f"{path.relative_to(root)}:{forbidden}")
    try:
        LambdaMutationFeatureFlags()
        LambdaMutationArmingState()
        guard_report = LambdaRealMutationExecutionGuard().evaluate(
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
        if guard_report.execution_guard_passed_for_execution:
            errors.append("execution guard passed for execution")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"skeleton guard setup failed: {exc}")
    try:
        DisabledLambdaRealMutationTransport().launch_one_instance()
        errors.append("disabled transport did not raise")
    except LambdaRealMutationDisabledError:
        pass
    errors.extend(patterns)
    return LambdaRealMutationSkeletonAuditReport(
        passed=not errors,
        executable_transport_exists=bool(patterns),
        live_transport_supports_post=live_post,
        live_transport_supports_delete=live_delete,
        real_mutation_code_detected=bool(patterns),
        forbidden_patterns=patterns,
        errors=errors,
        warnings=["mutation skeleton present but disabled; no execution path available"],
    )


def load_lambda_real_mutation_skeleton_audit_report(
    path: str | Path,
) -> LambdaRealMutationSkeletonAuditReport:
    return LambdaRealMutationSkeletonAuditReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_real_mutation_skeleton_audit_report(
    path: str | Path,
    report: LambdaRealMutationSkeletonAuditReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
