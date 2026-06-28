"""Future bounded integrated synthetic DiLoCo policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.integrated_diloco_command_discovery import (
    load_lambda_integrated_diloco_command_discovery,
)

LambdaIntegratedDilocoPolicyStatus = Literal[
    "policy_passed",
    "blocked_no_safe_command",
]


class LambdaIntegratedDilocoPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M084A"
    policy_status: LambdaIntegratedDilocoPolicyStatus
    one_instance: bool = True
    source_bundle_required: bool = True
    dependency_bundle_required: bool = True
    local_only_dependency_install: bool = True
    one_bounded_integrated_diloco_command: bool
    bounded_timeout: bool
    bounded_output: bool
    synthetic_only: bool
    learners: int = 1
    sync_rounds: int = 1
    inner_optimizer: str | None = None
    outer_optimizer: str | None = None
    expected_integrated_fidelity: str | None = None
    max_steps: int = 1
    no_internet: bool = True
    no_model_or_data_download: bool = True
    no_package_install_beyond_local_wheelhouse: bool = True
    no_real_training: bool = True
    no_background_process: bool = True
    no_parameter_fragment_claim_unless_active: bool = True
    halt_after_first_failed_live_stage: bool = True
    terminate_and_verify: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaIntegratedDilocoPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("integrated DiLoCo policy must remain future-only")
        if self.policy_status == "policy_passed" and self.blockers:
            raise ValueError("passing integrated DiLoCo policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_integrated_diloco_policy_from_path(
    *,
    command_discovery: str | Path,
) -> LambdaIntegratedDilocoPolicy:
    discovery = load_lambda_integrated_diloco_command_discovery(command_discovery)
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_integrated_diloco_command":
        blockers.append("no_safe_integrated_diloco_command_found")
    if not discovery.argv_tokens:
        blockers.append("integrated_diloco_command_missing")
    if discovery.timeout_seconds is None:
        blockers.append("integrated_diloco_timeout_missing")
    if not discovery.synthetic_only:
        blockers.append("integrated_diloco_not_synthetic")
    if discovery.learners != 1:
        blockers.append("integrated_diloco_learners_not_one")
    if discovery.sync_rounds != 1:
        blockers.append("integrated_diloco_sync_rounds_not_one")
    if discovery.inner_optimizer != "adamw":
        blockers.append("inner_optimizer_not_adamw")
    if discovery.outer_optimizer != "nesterov":
        blockers.append("outer_optimizer_not_nesterov")
    if (
        discovery.expected_integrated_fidelity
        != "integrated_optimizer_protocol_smoke"
    ):
        blockers.append("integrated_optimizer_protocol_smoke_not_expected")
    if discovery.max_steps != 1:
        blockers.append("integrated_diloco_max_steps_not_one")
    if not discovery.learner_syncer_protocol_required:
        blockers.append("learner_syncer_protocol_not_required")
    if not discovery.diloco_shaped_sync_round_required:
        blockers.append("diloco_sync_round_not_required")
    if not discovery.pseudo_gradient_semantics_required:
        blockers.append("pseudo_gradient_semantics_not_required")
    if not discovery.optimizer_state_roundtrip_required:
        blockers.append("optimizer_state_roundtrip_not_required")
    if not discovery.replay_or_metric_validation_required:
        blockers.append("replay_metric_validation_not_required")
    if discovery.parameter_fragment_claim_allowed:
        blockers.append("parameter_fragment_claim_allowed_without_active_fragments")
    if not discovery.no_external_network:
        blockers.append("integrated_diloco_network_allowed")
    if not discovery.no_downloads:
        blockers.append("integrated_diloco_download_allowed")
    if not discovery.no_package_install:
        blockers.append("integrated_diloco_package_install_allowed")
    if not discovery.no_real_training:
        blockers.append("integrated_diloco_training_allowed")
    if not discovery.no_background_process:
        blockers.append("integrated_diloco_background_allowed")
    if discovery.gpu_required:
        blockers.append("integrated_diloco_gpu_required")
    safe = not blockers
    return LambdaIntegratedDilocoPolicy(
        policy_status="policy_passed" if safe else "blocked_no_safe_command",
        one_bounded_integrated_diloco_command=safe,
        bounded_timeout=safe and discovery.timeout_seconds is not None,
        bounded_output=safe,
        synthetic_only=safe and discovery.synthetic_only,
        learners=discovery.learners,
        sync_rounds=discovery.sync_rounds,
        inner_optimizer=discovery.inner_optimizer,
        outer_optimizer=discovery.outer_optimizer,
        expected_integrated_fidelity=discovery.expected_integrated_fidelity,
        max_steps=discovery.max_steps,
        blockers=blockers,
        warnings=[
            "policy is future-only; M085R requires fresh gates and operator approval",
        ],
    )


def load_lambda_integrated_diloco_policy(path: str | Path) -> LambdaIntegratedDilocoPolicy:
    return LambdaIntegratedDilocoPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_integrated_diloco_policy(
    path: str | Path,
    report: LambdaIntegratedDilocoPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
