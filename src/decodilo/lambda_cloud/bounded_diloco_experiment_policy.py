"""Future M089R bounded synthetic DiLoCo experiment policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_discovery import (
    load_lambda_bounded_diloco_experiment_command_discovery,
)

LambdaBoundedDilocoExperimentPolicyStatus = Literal[
    "policy_passed",
    "blocked_no_safe_command",
]


class LambdaBoundedDilocoExperimentPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M088"
    policy_status: LambdaBoundedDilocoExperimentPolicyStatus
    one_instance: bool = True
    source_bundle_required: bool = True
    dependency_bundle_required: bool = True
    local_only_dependency_install: bool = True
    one_bounded_synthetic_diloco_experiment_command: bool
    bounded_timeout: bool
    bounded_output: bool
    synthetic_only: bool
    learners: int = 1
    sync_rounds: int = 1
    fragments: int = 2
    inner_optimizer: str = "adamw"
    outer_optimizer: str = "nesterov"
    max_steps: int = 1
    no_internet: bool = True
    no_model_or_data_download: bool = True
    no_package_install_beyond_local_wheelhouse: bool = True
    no_real_training: bool = True
    no_background_process: bool = True
    no_new_independent_smoke_category: bool = True
    halt_after_first_failed_live_stage: bool = True
    terminate_and_verify: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaBoundedDilocoExperimentPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("bounded experiment policy must remain future-only")
        if self.policy_status == "policy_passed" and self.blockers:
            raise ValueError("passing bounded experiment policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_bounded_diloco_experiment_policy_from_path(
    *,
    command_discovery: str | Path,
) -> LambdaBoundedDilocoExperimentPolicy:
    discovery = load_lambda_bounded_diloco_experiment_command_discovery(
        command_discovery
    )
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_bounded_diloco_experiment_command":
        blockers.append("no_safe_bounded_diloco_experiment_command_found")
    if not discovery.argv_tokens:
        blockers.append("bounded_diloco_experiment_command_missing")
    if discovery.timeout_seconds is None:
        blockers.append("bounded_diloco_experiment_timeout_missing")
    if not discovery.synthetic_only:
        blockers.append("bounded_diloco_experiment_not_synthetic")
    for field, expected in {
        "learners": 1,
        "sync_rounds": 1,
        "fragments": 2,
        "max_steps": 1,
    }.items():
        if getattr(discovery, field) != expected:
            blockers.append(f"bounded_diloco_experiment_{field}_mismatch")
    if discovery.inner_optimizer != "adamw":
        blockers.append("inner_optimizer_not_adamw")
    if discovery.outer_optimizer != "nesterov":
        blockers.append("outer_optimizer_not_nesterov")
    if not discovery.learner_syncer_protocol_required:
        blockers.append("learner_syncer_protocol_not_required")
    if not discovery.adamw_required or not discovery.nesterov_required:
        blockers.append("optimizer_semantics_not_required")
    if not discovery.pseudo_gradient_required:
        blockers.append("pseudo_gradient_not_required")
    if not discovery.parameter_fragments_required:
        blockers.append("parameter_fragments_not_required")
    if not discovery.replay_metric_validation_required:
        blockers.append("replay_metric_validation_not_required")
    if not discovery.no_external_network:
        blockers.append("bounded_experiment_network_allowed")
    if not discovery.no_downloads:
        blockers.append("bounded_experiment_download_allowed")
    if not discovery.no_package_install:
        blockers.append("bounded_experiment_package_install_allowed")
    if not discovery.no_real_training:
        blockers.append("bounded_experiment_training_allowed")
    if not discovery.no_background_process:
        blockers.append("bounded_experiment_background_allowed")
    if not discovery.no_new_independent_smoke_category:
        blockers.append("new_independent_smoke_category_allowed")
    if discovery.gpu_required:
        blockers.append("bounded_experiment_gpu_required")
    safe = not blockers
    return LambdaBoundedDilocoExperimentPolicy(
        policy_status="policy_passed" if safe else "blocked_no_safe_command",
        one_bounded_synthetic_diloco_experiment_command=safe,
        bounded_timeout=safe and discovery.timeout_seconds is not None,
        bounded_output=safe,
        synthetic_only=safe and discovery.synthetic_only,
        blockers=blockers,
        warnings=[
            "policy is future-only; M089R requires fresh gates and operator approval",
        ],
    )


def load_lambda_bounded_diloco_experiment_policy(
    path: str | Path,
) -> LambdaBoundedDilocoExperimentPolicy:
    return LambdaBoundedDilocoExperimentPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_bounded_diloco_experiment_policy(
    path: str | Path,
    report: LambdaBoundedDilocoExperimentPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
