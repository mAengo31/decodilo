"""Future-only M093R tiny real-training smoke authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.tiny_real_training_command_discovery import (
    load_lambda_tiny_real_training_command_discovery,
)
from decodilo.lambda_cloud.tiny_real_training_policy import (
    load_lambda_tiny_real_training_policy,
)
from decodilo.lambda_cloud.tiny_real_training_readiness import (
    load_lambda_tiny_real_training_readiness,
)

LambdaM093RTinyRealTrainingAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m093r_tiny_real_training_smoke",
]


class LambdaM093RTinyRealTrainingAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M092"
    authorization_status: LambdaM093RTinyRealTrainingAuthorizationStatus
    run_now: bool = False
    future_only: bool = True
    command_category: str | None = None
    max_launch_attempts: int = 1
    max_instances: int = 1
    max_training_steps: int = 1
    no_network: bool = True
    no_downloads: bool = True
    no_package_install_from_internet: bool = True
    cpu_only: bool = True
    torch_required: bool = False
    gpu_required: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_authorization(self) -> LambdaM093RTinyRealTrainingAuthorization:
        if self.launch_ready or self.launch_allowed or self.run_now:
            raise ValueError("M093R authorization is future-only and cannot run now")
        if self.billable_action_performed:
            raise ValueError("M092 authorization package cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m093r_tiny_real_training_smoke"
            and self.blockers
        ):
            raise ValueError("authorized future M093R package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m093r_tiny_real_training_authorization_from_paths(
    *,
    readiness: str | Path,
    command_discovery: str | Path,
    policy: str | Path,
) -> LambdaM093RTinyRealTrainingAuthorization:
    ready = load_lambda_tiny_real_training_readiness(readiness)
    discovery = load_lambda_tiny_real_training_command_discovery(command_discovery)
    training_policy = load_lambda_tiny_real_training_policy(policy)
    blockers: list[str] = []
    if ready.readiness_status != "ready_for_future_tiny_real_training_planning":
        blockers.append("tiny_real_training_readiness_not_ready")
    if discovery.discovery_status != "found_safe_tiny_real_training_command":
        blockers.append("tiny_real_training_smoke_not_verified")
    if training_policy.policy_status != "policy_passed":
        blockers.extend(training_policy.blockers or ["tiny_real_training_policy_blocked"])
    status: LambdaM093RTinyRealTrainingAuthorizationStatus = (
        "authorized_for_future_m093r_tiny_real_training_smoke"
        if not blockers
        else "not_authorized"
    )
    return LambdaM093RTinyRealTrainingAuthorization(
        authorization_status=status,
        command_category=discovery.command_category,
        torch_required=discovery.torch_required,
        gpu_required=discovery.gpu_required,
        blockers=sorted(set(blockers)),
        warnings=[
            "authorization is future-only and still requires fresh discovery and "
            "operator approval",
        ],
    )


def load_lambda_m093r_tiny_real_training_authorization(
    path: str | Path,
) -> LambdaM093RTinyRealTrainingAuthorization:
    return LambdaM093RTinyRealTrainingAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m093r_tiny_real_training_authorization(
    path: str | Path,
    report: LambdaM093RTinyRealTrainingAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
