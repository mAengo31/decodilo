"""Future next bounded synthetic experiment safety policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.next_synthetic_experiment_discovery import (
    load_lambda_next_synthetic_experiment_discovery,
)

LambdaNextSyntheticExperimentPolicyStatus = Literal[
    "policy_passed",
    "blocked_no_safe_command",
]


class LambdaNextSyntheticExperimentPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M078"
    policy_status: LambdaNextSyntheticExperimentPolicyStatus
    one_instance: bool = True
    source_bundle_required: bool = True
    dependency_bundle_required: bool = True
    local_only_dependency_install: bool = True
    one_bounded_synthetic_experiment_command: bool
    bounded_timeout: bool
    bounded_output: bool
    synthetic_only: bool
    no_internet: bool = True
    no_model_or_data_download: bool = True
    no_package_install_beyond_local_wheelhouse: bool = True
    no_real_training: bool = True
    no_background_process: bool = True
    halt_after_first_failed_live_stage: bool = True
    terminate_and_verify: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaNextSyntheticExperimentPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("next synthetic experiment policy must remain future-only")
        if self.policy_status == "policy_passed" and self.blockers:
            raise ValueError("passing next synthetic policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_next_synthetic_experiment_policy_from_path(
    *,
    command_discovery: str | Path,
) -> LambdaNextSyntheticExperimentPolicy:
    discovery = load_lambda_next_synthetic_experiment_discovery(command_discovery)
    blockers: list[str] = []
    if discovery.discovery_status != "found_safe_next_synthetic_experiment_command":
        blockers.append("no_safe_next_synthetic_experiment_command_found")
    if not discovery.argv_tokens:
        blockers.append("next_synthetic_experiment_command_missing")
    if discovery.timeout_seconds is None:
        blockers.append("next_synthetic_experiment_timeout_missing")
    if not discovery.synthetic_only:
        blockers.append("next_synthetic_experiment_not_synthetic")
    if not discovery.no_external_network:
        blockers.append("next_synthetic_experiment_network_allowed")
    if not discovery.no_downloads:
        blockers.append("next_synthetic_experiment_download_allowed")
    if not discovery.no_package_install:
        blockers.append("next_synthetic_experiment_package_install_allowed")
    if not discovery.no_real_training:
        blockers.append("next_synthetic_experiment_training_allowed")
    if not discovery.no_background_process:
        blockers.append("next_synthetic_experiment_background_allowed")
    if discovery.gpu_required:
        blockers.append("next_synthetic_experiment_gpu_required")
    safe = not blockers
    return LambdaNextSyntheticExperimentPolicy(
        policy_status="policy_passed" if safe else "blocked_no_safe_command",
        one_bounded_synthetic_experiment_command=safe,
        bounded_timeout=safe and discovery.timeout_seconds is not None,
        bounded_output=safe,
        synthetic_only=safe and discovery.synthetic_only,
        blockers=blockers,
        warnings=[
            "policy is future-only; M079R requires fresh gates and operator approval",
        ],
    )


def load_lambda_next_synthetic_experiment_policy(
    path: str | Path,
) -> LambdaNextSyntheticExperimentPolicy:
    return LambdaNextSyntheticExperimentPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_next_synthetic_experiment_policy(
    path: str | Path,
    report: LambdaNextSyntheticExperimentPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
