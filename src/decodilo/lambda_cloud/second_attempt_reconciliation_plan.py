"""Reconciliation plan for a future second Lambda launch attempt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

OwnershipConfidence = Literal["exact", "high", "medium", "low", "none"]


class LambdaSecondAttemptReconciliationPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    read_only_verify_after_launch_success: bool = True
    read_only_discovery_after_timeout: bool = True
    exact_owned_id_required_if_response_present: bool = True
    high_confidence_candidate_required_if_response_absent: bool = True
    terminate_disallowed_for_low_or_none_confidence: bool = True
    manual_console_review_if_ambiguous: bool = True
    read_only_termination_verification_after_terminate: bool = True
    final_ledger_reconciliation: bool = True
    candidate_confidence: OwnershipConfidence = "none"
    terminate_allowed_for_candidate: bool = False
    steps: list[str] = Field(default_factory=list)
    plan_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSecondAttemptReconciliationPlan:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("second-attempt reconciliation plan cannot enable launch")
        if (
            self.candidate_confidence in {"low", "none"}
            and self.terminate_allowed_for_candidate
        ):
            raise ValueError("low or no confidence candidate cannot be terminated")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_second_attempt_reconciliation_plan(
    *,
    candidate_confidence: OwnershipConfidence = "none",
) -> LambdaSecondAttemptReconciliationPlan:
    required = {
        "read_only_verify_after_launch_success": True,
        "read_only_discovery_after_timeout": True,
        "exact_owned_id_required_if_response_present": True,
        "high_confidence_candidate_required_if_response_absent": True,
        "terminate_disallowed_for_low_or_none_confidence": True,
        "manual_console_review_if_ambiguous": True,
        "read_only_termination_verification_after_terminate": True,
        "final_ledger_reconciliation": True,
    }
    blockers = [name for name, value in required.items() if not value]
    return LambdaSecondAttemptReconciliationPlan(
        **required,
        candidate_confidence=candidate_confidence,
        terminate_allowed_for_candidate=candidate_confidence in {"exact", "high"},
        steps=[
            "record owned instance id from launch response when present",
            "run read-only get/list after launch success",
            "run immediate read-only discovery after timeout or response loss",
            "match candidates by shape, region, and launch time window when available",
            "terminate only exact or high-confidence owned instance",
            "send no terminate request for low-confidence or absent candidates",
            "perform manual console review for ambiguous candidates",
            "verify termination through Lambda read-only get/list",
            "reconcile final ledger and journal",
        ],
        plan_passed=not blockers,
        blockers=blockers,
        warnings=["M030 reconciliation plan is non-executable review evidence"],
    )


def load_lambda_second_attempt_reconciliation_plan(
    path: str | Path,
) -> LambdaSecondAttemptReconciliationPlan:
    return LambdaSecondAttemptReconciliationPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_second_attempt_reconciliation_plan(
    path: str | Path,
    plan: LambdaSecondAttemptReconciliationPlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.to_json(), encoding="utf-8")
