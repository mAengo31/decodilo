"""M028 final teardown verification plan."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaFinalTeardownVerificationStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: str
    description: str
    read_only_verification: bool = False
    manual_review_trigger: bool = False
    non_executable: bool = True


class LambdaFinalTeardownVerificationPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    plan_id: str = "lambda-final-teardown-verification-plan-m028"
    owned_instance_id_source: str = "future launch response or read-only reconciliation"
    terminate_only_owned_instance: bool = True
    os_shutdown_insufficient: bool = True
    steps: list[LambdaFinalTeardownVerificationStep]
    executable_terminate_command_present: bool = False
    plan_passed: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaFinalTeardownVerificationPlan:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M028 teardown verification plan cannot enable launch")
        if self.executable_terminate_command_present:
            raise ValueError("M028 teardown plan must not contain executable terminate command")
        if not self.os_shutdown_insufficient:
            raise ValueError("M028 teardown plan must state OS shutdown is insufficient")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_final_teardown_verification_plan() -> LambdaFinalTeardownVerificationPlan:
    steps = [
        LambdaFinalTeardownVerificationStep(
            step_id="record-owned-instance-id",
            description="Record the owned instance ID before any future terminate attempt.",
        ),
        LambdaFinalTeardownVerificationStep(
            step_id="terminate-owned-only",
            description="Future M029 may target only the owned instance ID.",
        ),
        LambdaFinalTeardownVerificationStep(
            step_id="verify-terminal-read-only",
            description="Verify terminated or absent state through read-only list/get.",
            read_only_verification=True,
        ),
        LambdaFinalTeardownVerificationStep(
            step_id="timeout-manual-review",
            description="Timeout or unknown state requires manual review.",
            manual_review_trigger=True,
        ),
        LambdaFinalTeardownVerificationStep(
            step_id="collect-ledger-and-audit",
            description="Collect final ledger, read-only audit, and billable-action evidence.",
            read_only_verification=True,
        ),
    ]
    return LambdaFinalTeardownVerificationPlan(
        steps=steps,
        warnings=["M028 teardown verification plan is non-executable."],
    )


def load_lambda_final_teardown_verification_plan(
    path: str | Path,
) -> LambdaFinalTeardownVerificationPlan:
    return LambdaFinalTeardownVerificationPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_final_teardown_verification_plan(
    path: str | Path,
    plan: LambdaFinalTeardownVerificationPlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.to_json(), encoding="utf-8")

