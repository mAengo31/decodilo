"""Staged rollout plan for a future remote backend implementation.

Milestone 017 only defines the phases. It does not implement any later phase.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RemoteBackendRollbackPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    steps: list[str]
    rollback_possible: bool = True


class RemoteBackendExitCriteria(BaseModel):
    model_config = ConfigDict(frozen=True)

    success_criteria: list[str]
    failure_criteria: list[str]


class RemoteBackendRolloutPhase(BaseModel):
    model_config = ConfigDict(frozen=True)

    phase_id: str
    allowed_operations: list[str]
    forbidden_operations: list[str]
    required_evidence: list[str]
    budget_limit: float | None = Field(default=None, ge=0)
    teardown_or_cleanup_plan: list[str]
    rollback_plan: RemoteBackendRollbackPlan
    exit_criteria: RemoteBackendExitCriteria
    manual_approval_required: bool = True
    current_phase: bool = False
    remote_backend_enabled: bool = False


class RemoteBackendRolloutPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    rollout_schema_version: int = 1
    proposal_ref: str | None = None
    current_phase_id: str = "phase_0_design_only"
    phases: list[RemoteBackendRolloutPhase]
    warnings: list[str] = Field(default_factory=list)
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_no_enabled_phase(self) -> RemoteBackendRolloutPlan:
        if self.remote_backend_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("rollout plan cannot enable backend or launch")
        enabled = [phase.phase_id for phase in self.phases if phase.remote_backend_enabled]
        if enabled:
            raise ValueError(f"no rollout phase can be enabled in M017: {enabled}")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_remote_backend_rollout_plan(
    *,
    proposal_ref: str | None = None,
) -> RemoteBackendRolloutPlan:
    phases = [
        _phase(
            "phase_0_design_only",
            ["write local proposal artifacts"],
            ["add SDK", "read credentials", "network calls", "remote writes"],
            current=True,
        ),
        _phase("phase_1_sdk_import_only_disabled", ["review dependency diff"], ["enable backend"]),
        _phase(
            "phase_2_fake_credentials_no_network",
            ["validate symbolic auth"],
            ["real credentials"],
        ),
        _phase("phase_3_read_only_metadata_discovery", ["future metadata read"], ["writes"]),
        _phase(
            "phase_4_write_to_sandbox_bucket_or_equivalent",
            ["future sandbox write"],
            ["production data"],
        ),
        _phase(
            "phase_5_single_node_artifact_smoke",
            ["future smoke test"],
            ["multi-tenant launch"],
        ),
        _phase(
            "phase_6_multi_learner_artifact_smoke",
            ["future local scale smoke"],
            ["cloud launch"],
        ),
        _phase(
            "phase_7_scale_test_under_budget",
            ["future budgeted scale test"],
            ["unbounded spend"],
        ),
    ]
    return RemoteBackendRolloutPlan(
        proposal_ref=proposal_ref,
        phases=phases,
        warnings=["only phase_0_design_only is current; later phases are plan text"],
    )


def load_remote_backend_rollout_plan(path: str | Path) -> RemoteBackendRolloutPlan:
    return RemoteBackendRolloutPlan.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_remote_backend_rollout_plan(path: str | Path, plan: RemoteBackendRolloutPlan) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.to_json(), encoding="utf-8")


def _phase(
    phase_id: str,
    allowed: list[str],
    forbidden: list[str],
    *,
    current: bool = False,
) -> RemoteBackendRolloutPhase:
    return RemoteBackendRolloutPhase(
        phase_id=phase_id,
        allowed_operations=allowed,
        forbidden_operations=forbidden,
        required_evidence=["human approval", "updated preflight evidence"],
        budget_limit=0.0 if current else None,
        teardown_or_cleanup_plan=["no live resources in current milestone"],
        rollback_plan=RemoteBackendRollbackPlan(steps=["revert proposal artifact"]),
        exit_criteria=RemoteBackendExitCriteria(
            success_criteria=["review artifact complete"],
            failure_criteria=["missing evidence", "guard failure"],
        ),
        manual_approval_required=True,
        current_phase=current,
        remote_backend_enabled=False,
    )
