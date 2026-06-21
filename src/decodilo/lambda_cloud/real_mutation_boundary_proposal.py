"""Review-only real Lambda mutation boundary proposal for M023."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.first_launch_failure_modes import (
    LambdaFirstLaunchFailureModeTable,
    build_lambda_first_launch_failure_mode_table,
)
from decodilo.lambda_cloud.first_launch_safety_case import (
    LambdaFirstLaunchSafetyCase,
    build_lambda_first_launch_safety_case,
)
from decodilo.lambda_cloud.real_mutation_arming_gate import (
    LambdaRealMutationArmingGateDesign,
    build_lambda_real_mutation_arming_gate_design,
)
from decodilo.lambda_cloud.real_mutation_kill_switch_design import (
    LambdaKillSwitchDesign,
    build_lambda_kill_switch_design,
)
from decodilo.lambda_cloud.real_mutation_operation_spec import (
    LambdaRealMutationOperationSet,
    build_lambda_real_mutation_operation_set,
)
from decodilo.lambda_cloud.real_teardown_safety_case import (
    LambdaRealTeardownSafetyCase,
    build_lambda_real_teardown_safety_case,
)

LambdaRealMutationBoundaryStatus = Literal[
    "draft",
    "evidence_incomplete",
    "review_ready",
    "blocked",
]


class LambdaRealMutationBoundaryScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposed_future_scope: list[str] = Field(default_factory=list)
    excluded_scope: list[str] = Field(default_factory=list)


class LambdaRealMutationBoundaryNonGoals(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[str] = Field(default_factory=list)


class LambdaRealMutationBoundaryProposal(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposal_schema_version: int = 1
    proposal_id: str
    created_at_utc: str | None = None
    source_m019c_discovery_ref: str
    source_m020_report_ref: str
    source_m022_fake_readiness_package_ref: str
    source_real_mutation_absence_audit_ref: str
    operation_set: LambdaRealMutationOperationSet
    arming_gate: LambdaRealMutationArmingGateDesign
    arming_gate_ref: str | None = None
    kill_switch_design: LambdaKillSwitchDesign
    kill_switch_design_ref: str | None = None
    teardown_safety_case: LambdaRealTeardownSafetyCase
    teardown_safety_case_ref: str | None = None
    first_launch_safety_case: LambdaFirstLaunchSafetyCase
    first_launch_safety_case_ref: str | None = None
    failure_modes: LambdaFirstLaunchFailureModeTable
    failure_modes_ref: str | None = None
    approval_evidence_ref: str | None = None
    scope: LambdaRealMutationBoundaryScope
    non_goals: LambdaRealMutationBoundaryNonGoals
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    boundary_status: LambdaRealMutationBoundaryStatus = "draft"
    real_mutation_transport_implemented: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled_in_m023(self) -> LambdaRealMutationBoundaryProposal:
        if (
            self.real_mutation_transport_implemented
            or self.real_mutation_enabled
            or self.launch_ready
            or self.launch_allowed
        ):
            raise ValueError("M023 proposal cannot enable mutation or launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_real_mutation_boundary_proposal(
    *,
    m019c_discovery: str | Path,
    m020_report: str | Path,
    m022_readiness_package: str | Path,
    real_mutation_absence_audit: str | Path,
    proposal_id: str = "lambda-real-mutation-boundary-proposal-m023",
) -> LambdaRealMutationBoundaryProposal:
    refs = {
        "m019c_discovery": Path(m019c_discovery),
        "m020_report": Path(m020_report),
        "m022_readiness_package": Path(m022_readiness_package),
        "real_mutation_absence_audit": Path(real_mutation_absence_audit),
    }
    blockers = [
        f"missing evidence: {name}" for name, path in refs.items() if not path.exists()
    ]
    if not refs["m022_readiness_package"].exists():
        blockers.append("fake launch readiness package is required before real mutation review")
    status: LambdaRealMutationBoundaryStatus = (
        "review_ready" if not blockers else "evidence_incomplete"
    )
    operation_set = build_lambda_real_mutation_operation_set()
    arming_gate = build_lambda_real_mutation_arming_gate_design()
    kill_switch = build_lambda_kill_switch_design()
    teardown_case = build_lambda_real_teardown_safety_case(kill_switch_design=kill_switch)
    safety_case = build_lambda_first_launch_safety_case(
        operation_spec=operation_set,
        fake_lifecycle_evidence_ref=m022_readiness_package,
        termination_policy=teardown_case.termination_policy,
    )
    scope = LambdaRealMutationBoundaryScope(
        proposed_future_scope=[
            "launch exactly one approved instance",
            "read-only list/get verification",
            "terminate exactly one ledger-owned instance",
        ],
        excluded_scope=_default_non_goals(),
    )
    return LambdaRealMutationBoundaryProposal(
        proposal_id=proposal_id,
        source_m019c_discovery_ref=str(m019c_discovery),
        source_m020_report_ref=str(m020_report),
        source_m022_fake_readiness_package_ref=str(m022_readiness_package),
        source_real_mutation_absence_audit_ref=str(real_mutation_absence_audit),
        operation_set=operation_set,
        arming_gate=arming_gate,
        kill_switch_design=kill_switch,
        teardown_safety_case=teardown_case,
        first_launch_safety_case=safety_case,
        failure_modes=build_lambda_first_launch_failure_mode_table(),
        scope=scope,
        non_goals=LambdaRealMutationBoundaryNonGoals(items=_default_non_goals()),
        blockers=blockers,
        warnings=[
            "Review-only proposal; no real Lambda mutation transport is implemented.",
            "Design review readiness does not approve launch.",
        ],
        boundary_status=status,
    )


def _default_non_goals() -> list[str]:
    return [
        "no training",
        "no multi-node launch",
        "no setup scripts",
        "no SSH",
        "no filesystem creation",
        "no SSH key creation",
        "no restart",
        "no auto-scaling",
        "no background operation",
        "no unattended launch",
        "no production use",
    ]


def load_lambda_real_mutation_boundary_proposal(
    path: str | Path,
) -> LambdaRealMutationBoundaryProposal:
    return LambdaRealMutationBoundaryProposal.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_real_mutation_boundary_proposal(
    path: str | Path,
    proposal: LambdaRealMutationBoundaryProposal,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(proposal.to_json(), encoding="utf-8")
