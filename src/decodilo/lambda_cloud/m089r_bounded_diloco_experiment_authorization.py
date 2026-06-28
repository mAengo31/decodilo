"""Future-only M089R bounded synthetic DiLoCo experiment authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_discovery import (
    load_lambda_bounded_diloco_experiment_command_discovery,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_policy import (
    load_lambda_bounded_diloco_experiment_policy,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_readiness import (
    load_lambda_bounded_diloco_experiment_readiness,
)

LambdaM089RBoundedDilocoExperimentAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m089r_bounded_diloco_experiment",
]


class LambdaM089RBoundedDilocoExperimentAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M088"
    authorization_status: LambdaM089RBoundedDilocoExperimentAuthorizationStatus
    run_now: bool = False
    future_only: bool = True
    command_category: str | None = None
    max_launch_attempts: int = 1
    max_instances: int = 1
    halt_after_first_failed_live_stage: bool = True
    no_internet_install: bool = True
    no_downloads: bool = True
    no_real_training: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_authorization(self) -> LambdaM089RBoundedDilocoExperimentAuthorization:
        if self.launch_ready or self.launch_allowed or self.run_now:
            raise ValueError("M089R authorization is future-only and cannot run now")
        if self.billable_action_performed:
            raise ValueError("M088 authorization package cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m089r_bounded_diloco_experiment"
            and self.blockers
        ):
            raise ValueError("authorized future M089R package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m089r_bounded_diloco_experiment_authorization_from_paths(
    *,
    readiness: str | Path,
    command_discovery: str | Path,
    policy: str | Path,
) -> LambdaM089RBoundedDilocoExperimentAuthorization:
    ready = load_lambda_bounded_diloco_experiment_readiness(readiness)
    discovery = load_lambda_bounded_diloco_experiment_command_discovery(
        command_discovery
    )
    bounded_policy = load_lambda_bounded_diloco_experiment_policy(policy)
    blockers: list[str] = []
    if (
        ready.readiness_status
        != "ready_for_first_bounded_synthetic_diloco_experiment_planning"
    ):
        blockers.append("bounded_diloco_experiment_readiness_not_ready")
    if discovery.discovery_status != "found_safe_bounded_diloco_experiment_command":
        blockers.append("no_safe_bounded_diloco_experiment_command_found")
    if bounded_policy.policy_status != "policy_passed":
        blockers.append("bounded_diloco_experiment_policy_not_passed")
    status: LambdaM089RBoundedDilocoExperimentAuthorizationStatus = (
        "authorized_for_future_m089r_bounded_diloco_experiment"
        if not blockers
        else "not_authorized"
    )
    return LambdaM089RBoundedDilocoExperimentAuthorization(
        authorization_status=status,
        command_category=discovery.command_category,
        blockers=blockers,
        warnings=[
            "authorization is future-only and still requires fresh discovery and "
            "operator approval",
        ],
    )


def load_lambda_m089r_bounded_diloco_experiment_authorization(
    path: str | Path,
) -> LambdaM089RBoundedDilocoExperimentAuthorization:
    return LambdaM089RBoundedDilocoExperimentAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m089r_bounded_diloco_experiment_authorization(
    path: str | Path,
    report: LambdaM089RBoundedDilocoExperimentAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
