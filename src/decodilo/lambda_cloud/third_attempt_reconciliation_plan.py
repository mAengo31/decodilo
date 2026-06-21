"""Reconciliation plan for a future M034 third Lambda launch attempt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

OwnershipConfidence = Literal["exact", "high", "medium", "low", "none"]


class LambdaThirdAttemptReconciliationPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    verify_and_terminate_owned_id_from_response: bool = True
    read_only_reconciliation_after_response_loss: bool = True
    no_candidate_requires_manual_console_review: bool = True
    exact_or_high_confidence_candidate_terminable: bool = True
    medium_low_none_candidate_not_automatically_terminable: bool = True
    final_read_only_termination_verification_required: bool = True
    final_ledger_reconciliation_required: bool = True
    candidate_confidence: OwnershipConfidence = "none"
    terminate_allowed_for_candidate: bool = False
    steps: list[str] = Field(default_factory=list)
    plan_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaThirdAttemptReconciliationPlan:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("third-attempt reconciliation plan cannot enable launch")
        if (
            self.candidate_confidence in {"medium", "low", "none"}
            and self.terminate_allowed_for_candidate
        ):
            raise ValueError("medium/low/no confidence candidate cannot auto-terminate")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_third_attempt_reconciliation_plan(
    *,
    candidate_confidence: OwnershipConfidence = "none",
) -> LambdaThirdAttemptReconciliationPlan:
    required = {
        "verify_and_terminate_owned_id_from_response": True,
        "read_only_reconciliation_after_response_loss": True,
        "no_candidate_requires_manual_console_review": True,
        "exact_or_high_confidence_candidate_terminable": True,
        "medium_low_none_candidate_not_automatically_terminable": True,
        "final_read_only_termination_verification_required": True,
        "final_ledger_reconciliation_required": True,
    }
    blockers = [name for name, value in required.items() if not value]
    return LambdaThirdAttemptReconciliationPlan(
        **required,
        candidate_confidence=candidate_confidence,
        terminate_allowed_for_candidate=candidate_confidence in {"exact", "high"},
        steps=[
            "if launch response has owned id, verify running/readable state",
            "terminate only the recorded owned id",
            "if launch response is lost, run read-only list/get reconciliation",
            "if no candidate appears, require manual console review per policy",
            "if exact/high confidence candidate appears, terminate owned only",
            "if confidence is medium, low, or none, do not auto-terminate",
            "verify termination with read-only get/list",
            "write final ledger reconciliation",
        ],
        plan_passed=not blockers,
        blockers=blockers,
        warnings=["M033 reconciliation plan is review-only and cannot terminate"],
    )


def load_lambda_third_attempt_reconciliation_plan(
    path: str | Path,
) -> LambdaThirdAttemptReconciliationPlan:
    return LambdaThirdAttemptReconciliationPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_third_attempt_reconciliation_plan(
    path: str | Path,
    plan: LambdaThirdAttemptReconciliationPlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.to_json(), encoding="utf-8")
