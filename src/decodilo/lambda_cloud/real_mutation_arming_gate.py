"""Design-only arming gate for future Lambda real mutation review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaRealMutationArmingCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    criterion_id: str
    description: str
    required: bool = True


class LambdaRealMutationArmingGateDesign(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate_id: str = "lambda-real-mutation-arming-gate-m023"
    arming_gate_status: Literal["design_only"] = "design_only"
    criteria: list[LambdaRealMutationArmingCriterion]
    armed: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _cannot_arm(self) -> LambdaRealMutationArmingGateDesign:
        if self.armed or self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M023 arming gate is design-only and cannot arm")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRealMutationArmingReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate: LambdaRealMutationArmingGateDesign
    completed_criteria: list[str] = Field(default_factory=list)
    missing_criteria: list[str] = Field(default_factory=list)
    arming_gate_status: Literal["design_only"] = "design_only"
    armed: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _cannot_emit_enabled(self) -> LambdaRealMutationArmingReport:
        if self.armed or self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M023 arming report cannot enable mutation or launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_real_mutation_arming_gate_design() -> LambdaRealMutationArmingGateDesign:
    criteria = [
        ("operator_real_launch_review", "Explicit operator approval for real launch review."),
        ("max_budget", "Explicit max budget is fixed and acknowledged."),
        ("max_runtime", "Explicit max runtime is fixed and acknowledged."),
        ("max_instances_one", "Maximum instance count is exactly one."),
        ("shape_and_region", "Instance type, GPU shape, and region are explicit."),
        ("fresh_live_discovery", "Live read-only discovery is recent enough."),
        ("fresh_price_reconciliation", "Price reconciliation is fresh and non-ambiguous."),
        ("budget_manifest", "Budget manifest is valid and hash-locked."),
        ("clean_resource_ledger", "Resource ledger has no unmanaged billable resources."),
        ("teardown_plan", "Teardown plan is present and valid."),
        (
            "termination_verification_policy",
            "Termination verification policy is present and valid.",
        ),
        ("fake_lifecycle_stress", "Fake lifecycle stress package passes."),
        ("fake_teardown_audit", "Fake teardown audit passes."),
        (
            "real_mutation_absence_audit",
            "Real mutation absence audit passes before any mutation code is added.",
        ),
        ("implementation_review", "Mutation implementation review is complete."),
        ("dry_run_plan_hash", "Dry-run launch plan hash is locked."),
        ("approval_manifest_hash", "Approval manifest hash is locked."),
        ("idempotency_key", "Idempotency key is generated and recorded."),
        ("kill_switch_plan", "Kill-switch and emergency teardown design is present."),
        ("manual_operator_present", "Manual operator is present during launch window."),
        ("no_background_work", "No background launch work is allowed."),
        ("safe_retry_policy", "No auto-retry beyond configured safe policy."),
        ("launch_window_active", "Future launch window is active and bounded."),
    ]
    return LambdaRealMutationArmingGateDesign(
        criteria=[
            LambdaRealMutationArmingCriterion(criterion_id=criterion_id, description=description)
            for criterion_id, description in criteria
        ],
        warnings=["Design only; even complete criteria cannot arm real mutation in M023."],
    )


def evaluate_lambda_real_mutation_arming_gate(
    *,
    completed_criteria: set[str] | None = None,
    gate: LambdaRealMutationArmingGateDesign | None = None,
) -> LambdaRealMutationArmingReport:
    effective = gate or build_lambda_real_mutation_arming_gate_design()
    completed = completed_criteria or set()
    required = [criterion.criterion_id for criterion in effective.criteria if criterion.required]
    missing = [criterion_id for criterion_id in required if criterion_id not in completed]
    return LambdaRealMutationArmingReport(
        gate=effective,
        completed_criteria=sorted(completed),
        missing_criteria=missing,
        blockers=[f"missing criterion: {criterion_id}" for criterion_id in missing],
        warnings=["Arming remains design_only in M023."],
    )


def load_lambda_real_mutation_arming_gate_design(
    path: str | Path,
) -> LambdaRealMutationArmingGateDesign:
    return LambdaRealMutationArmingGateDesign.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_real_mutation_arming_gate_design(
    path: str | Path,
    design: LambdaRealMutationArmingGateDesign,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(design.to_json(), encoding="utf-8")
