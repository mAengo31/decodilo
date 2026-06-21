"""Design-only termination verification policy for future Lambda mutation review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaTerminationVerificationStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: str
    description: str
    required: bool = True
    read_only: bool = True


class LambdaTerminationVerificationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_schema_version: int = 1
    policy_id: str = "lambda-termination-verification-policy-m023"
    design_only: bool = True
    require_owned_instance_id_before_launch: bool = True
    terminate_only_owned_instance_id: bool = True
    require_read_only_poll: bool = True
    require_absent_or_terminal_state: bool = True
    require_ledger_reconciliation: bool = True
    require_final_status_record: bool = True
    fail_on_timeout: bool = True
    manual_review_on_unknown_state: bool = True
    os_shutdown_is_sufficient: bool = False
    allow_unowned_termination: bool = False
    real_termination_code_implemented: bool = False
    steps: list[LambdaTerminationVerificationStep] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaTerminationVerificationPolicy:
        if self.allow_unowned_termination:
            raise ValueError("termination policy cannot allow unowned termination")
        if self.os_shutdown_is_sufficient:
            raise ValueError("OS shutdown is not sufficient termination verification")
        if self.real_termination_code_implemented or self.launch_ready or self.launch_allowed:
            raise ValueError("M023 termination policy is design-only and non-launchable")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaTerminationVerificationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    policy: LambdaTerminationVerificationPolicy
    status: Literal["design_only", "blocked"] = "design_only"
    owned_instance_id_required: bool = True
    unowned_termination_rejected: bool = True
    read_only_verification_required: bool = True
    os_shutdown_insufficient: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_termination_verification_policy() -> LambdaTerminationVerificationPolicy:
    steps = [
        LambdaTerminationVerificationStep(
            step_id="record_owned_instance_id",
            description="Record the ledger-owned instance id before any future launch.",
        ),
        LambdaTerminationVerificationStep(
            step_id="terminate_only_owned_id",
            description="Future termination may target only the recorded owned instance id.",
            read_only=False,
        ),
        LambdaTerminationVerificationStep(
            step_id="poll_read_only_status",
            description="Poll read-only list/get until the instance is absent or terminal.",
        ),
        LambdaTerminationVerificationStep(
            step_id="reconcile_ledger",
            description="Reconcile resource ledger and record final terminal status.",
        ),
    ]
    return LambdaTerminationVerificationPolicy(steps=steps)


def evaluate_lambda_termination_verification_policy(
    policy: LambdaTerminationVerificationPolicy | None = None,
) -> LambdaTerminationVerificationReport:
    effective = policy or build_lambda_termination_verification_policy()
    errors: list[str] = []
    if not effective.require_owned_instance_id_before_launch:
        errors.append("owned instance id is required before launch")
    if not effective.terminate_only_owned_instance_id:
        errors.append("termination must be restricted to owned instance id")
    if not effective.require_read_only_poll:
        errors.append("read-only verification poll is required")
    if effective.os_shutdown_is_sufficient:
        errors.append("OS shutdown cannot be treated as sufficient termination")
    return LambdaTerminationVerificationReport(
        policy=effective,
        status="blocked" if errors else "design_only",
        errors=errors,
        warnings=["Policy only; no real termination code exists in M023."],
    )


def load_lambda_termination_verification_policy(
    path: str | Path,
) -> LambdaTerminationVerificationPolicy:
    return LambdaTerminationVerificationPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_termination_verification_policy(
    path: str | Path,
    policy: LambdaTerminationVerificationPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(policy.to_json(), encoding="utf-8")


def write_lambda_termination_verification_report(
    path: str | Path,
    report: LambdaTerminationVerificationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
