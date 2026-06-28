"""Future M093R tiny real-training smoke policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.tiny_real_training_command_discovery import (
    load_lambda_tiny_real_training_command_discovery,
)

LambdaTinyRealTrainingPolicyStatus = Literal[
    "policy_passed",
    "blocked_no_safe_command",
    "blocked_torch_dependency_unconfirmed",
]


class LambdaTinyRealTrainingPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M092"
    policy_status: LambdaTinyRealTrainingPolicyStatus
    one_instance: bool = True
    source_bundle_required: bool = True
    dependency_bundle_required: bool = True
    local_only_dependency_install: bool = True
    one_tiny_real_training_command: bool
    bounded_timeout: bool
    bounded_output: bool
    synthetic_only: bool
    model: str = "tiny-linear"
    steps: int = 1
    optimizer: str = "adamw"
    cpu_only: bool = True
    torch_required: bool = False
    gpu_required: bool = False
    no_network: bool = True
    no_package_install_beyond_local_wheelhouse: bool = True
    no_dataset_or_model_download: bool = True
    no_long_running_training: bool = True
    no_background_process: bool = True
    real_training_mechanics_required: bool = True
    no_real_model_scale_claim: bool = True
    no_paper_scale_training_claim: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaTinyRealTrainingPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("tiny real training policy must remain future-only")
        if self.policy_status == "policy_passed" and self.blockers:
            raise ValueError("passing tiny real training policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_tiny_real_training_policy_from_path(
    *,
    command_discovery: str | Path,
) -> LambdaTinyRealTrainingPolicy:
    discovery = load_lambda_tiny_real_training_command_discovery(command_discovery)
    blockers: list[str] = []
    torch_blocker = False
    if discovery.discovery_status != "found_safe_tiny_real_training_command":
        blockers.append("no_safe_tiny_real_training_command_found")
    if not discovery.argv_tokens:
        blockers.append("tiny_real_training_command_missing")
    if discovery.timeout_seconds is None:
        blockers.append("tiny_real_training_timeout_missing")
    if not discovery.synthetic_only:
        blockers.append("tiny_real_training_not_synthetic")
    if discovery.model != "tiny-linear":
        blockers.append("tiny_real_training_model_not_tiny_linear")
    if discovery.steps != 1:
        blockers.append("tiny_real_training_steps_not_one")
    if discovery.optimizer != "adamw":
        blockers.append("tiny_real_training_optimizer_not_adamw")
    if not discovery.cpu_only or discovery.gpu_required:
        blockers.append("tiny_real_training_not_cpu_only")
    if discovery.torch_required:
        blockers.append("torch_required_without_remote_dependency_confirmation")
        torch_blocker = True
    if not discovery.training_attempted:
        blockers.append("tiny_real_training_not_attempted")
    if not discovery.real_training_mechanics_exercised:
        blockers.append("tiny_real_training_mechanics_not_verified")
    if not discovery.no_external_network:
        blockers.append("tiny_real_training_network_allowed")
    if not discovery.no_package_install:
        blockers.append("tiny_real_training_package_install_allowed")
    if not discovery.no_downloads:
        blockers.append("tiny_real_training_download_allowed")
    if not discovery.no_dataset_download or not discovery.no_model_download:
        blockers.append("tiny_real_training_dataset_model_download_allowed")
    if not discovery.no_background_process:
        blockers.append("tiny_real_training_background_allowed")
    if not discovery.bounded_runtime or not discovery.bounded_output:
        blockers.append("tiny_real_training_not_bounded")
    if torch_blocker:
        status: LambdaTinyRealTrainingPolicyStatus = (
            "blocked_torch_dependency_unconfirmed"
        )
    else:
        status = "policy_passed" if not blockers else "blocked_no_safe_command"
    safe = status == "policy_passed"
    return LambdaTinyRealTrainingPolicy(
        policy_status=status,
        one_tiny_real_training_command=safe,
        bounded_timeout=safe,
        bounded_output=safe,
        synthetic_only=safe and discovery.synthetic_only,
        torch_required=discovery.torch_required,
        gpu_required=discovery.gpu_required,
        blockers=blockers,
        warnings=[
            "policy is future-only; M093R requires fresh gates and operator approval",
        ],
    )


def load_lambda_tiny_real_training_policy(
    path: str | Path,
) -> LambdaTinyRealTrainingPolicy:
    return LambdaTinyRealTrainingPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_tiny_real_training_policy(
    path: str | Path,
    report: LambdaTinyRealTrainingPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
