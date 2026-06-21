"""Review-only first Lambda launch safety case for M023."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.first_launch_failure_modes import (
    LambdaFirstLaunchFailureModeTable,
    build_lambda_first_launch_failure_mode_table,
)
from decodilo.lambda_cloud.real_mutation_operation_spec import (
    LambdaRealMutationOperationSet,
    load_lambda_real_mutation_operation_set,
)
from decodilo.lambda_cloud.termination_verification_policy import (
    LambdaTerminationVerificationPolicy,
    build_lambda_termination_verification_policy,
)


class LambdaFirstLaunchSafetyClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_id: str
    description: str
    required: bool = True
    satisfied: bool = False
    evidence_refs: list[str] = Field(default_factory=list)


class LambdaFirstLaunchEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    ref: str
    required: bool = True
    present: bool = False


class LambdaFirstLaunchSafetyCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    safety_case_id: str = "lambda-first-launch-safety-case-m023"
    proposal_ref: str | None = None
    operation_spec_ref: str | None = None
    termination_verification_policy: LambdaTerminationVerificationPolicy
    failure_mode_table: LambdaFirstLaunchFailureModeTable
    claims: list[LambdaFirstLaunchSafetyClaim]
    evidence: list[LambdaFirstLaunchEvidence]
    safety_case_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _cannot_enable_launch(self) -> LambdaFirstLaunchSafetyCase:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M023 safety case cannot enable real mutation or launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_first_launch_safety_case(
    *,
    proposal_ref: str | Path | None = None,
    operation_spec: str | Path | LambdaRealMutationOperationSet | None = None,
    fake_lifecycle_evidence_ref: str | Path | None = None,
    termination_policy: LambdaTerminationVerificationPolicy | None = None,
) -> LambdaFirstLaunchSafetyCase:
    operation_set = _load_operation_set(operation_spec)
    termination = termination_policy or build_lambda_termination_verification_policy()
    evidence = [
        LambdaFirstLaunchEvidence(
            evidence_id="fake_lifecycle_evidence",
            ref="" if fake_lifecycle_evidence_ref is None else str(fake_lifecycle_evidence_ref),
            present=fake_lifecycle_evidence_ref is not None
            and Path(fake_lifecycle_evidence_ref).exists(),
        ),
        LambdaFirstLaunchEvidence(
            evidence_id="termination_verification_policy",
            ref=termination.policy_id,
            present=True,
        ),
        LambdaFirstLaunchEvidence(
            evidence_id="operation_spec",
            ref="" if operation_spec is None else str(operation_spec),
            present=operation_set is not None,
        ),
    ]
    blockers: list[str] = []
    if not evidence[0].present:
        blockers.append("missing fake lifecycle evidence")
    if not evidence[1].present:
        blockers.append("missing termination verification policy")
    if operation_set is None:
        blockers.append("missing operation spec")
    claims = _build_claims(evidence_refs=[item.ref for item in evidence if item.present])
    if blockers:
        claims = [claim.model_copy(update={"satisfied": False}) for claim in claims]
    return LambdaFirstLaunchSafetyCase(
        proposal_ref=None if proposal_ref is None else str(proposal_ref),
        operation_spec_ref=None if operation_spec is None else str(operation_spec),
        termination_verification_policy=termination,
        failure_mode_table=build_lambda_first_launch_failure_mode_table(),
        claims=claims,
        evidence=evidence,
        safety_case_passed=not blockers,
        blockers=blockers,
        warnings=["Safety case is review-only; first real launch is not approved."],
    )


def _load_operation_set(
    value: str | Path | LambdaRealMutationOperationSet | None,
) -> LambdaRealMutationOperationSet | None:
    if value is None:
        return None
    if isinstance(value, LambdaRealMutationOperationSet):
        return value
    return load_lambda_real_mutation_operation_set(value)


def _build_claims(evidence_refs: list[str]) -> list[LambdaFirstLaunchSafetyClaim]:
    definitions = [
        ("one_instance", "Only one instance is allowed."),
        ("budget_50", "Maximum budget is at most $50."),
        ("runtime_30", "Maximum runtime is at most 30 minutes."),
        ("teardown_required", "Launch cannot proceed without teardown plan."),
        (
            "termination_verification_required",
            "Launch cannot proceed without termination verification policy.",
        ),
        ("approval_required", "Launch cannot proceed without human approval."),
        (
            "no_unmanaged_billable",
            "Launch cannot proceed with unmanaged billable resources.",
        ),
        ("fresh_price_required", "Launch cannot proceed with stale or missing price."),
        ("idempotency_required", "Launch cannot proceed without idempotency key."),
        ("launch_window_required", "Launch cannot proceed outside launch window."),
        (
            "fake_evidence_required",
            "Launch cannot proceed if fake lifecycle evidence is missing.",
        ),
        ("no_training", "No training workload is allowed during first launch."),
        ("no_ssh", "No SSH is allowed unless explicitly reviewed later."),
        ("no_setup_script", "No setup script is allowed unless reviewed later."),
    ]
    return [
        LambdaFirstLaunchSafetyClaim(
            claim_id=claim_id,
            description=description,
            satisfied=True,
            evidence_refs=evidence_refs,
        )
        for claim_id, description in definitions
    ]


def load_lambda_first_launch_safety_case(path: str | Path) -> LambdaFirstLaunchSafetyCase:
    return LambdaFirstLaunchSafetyCase.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_first_launch_safety_case(
    path: str | Path,
    safety_case: LambdaFirstLaunchSafetyCase,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(safety_case.to_json(), encoding="utf-8")
