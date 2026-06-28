"""Future-only M085R bounded integrated synthetic DiLoCo authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.integrated_diloco_command_discovery import (
    load_lambda_integrated_diloco_command_discovery,
)
from decodilo.lambda_cloud.integrated_diloco_policy import (
    load_lambda_integrated_diloco_policy,
)
from decodilo.lambda_cloud.integrated_diloco_synthetic_readiness import (
    load_lambda_integrated_diloco_synthetic_readiness,
)

LambdaM085RIntegratedDilocoAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m085r_integrated_diloco_smoke",
]


class LambdaM085RIntegratedDilocoAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M084A"
    authorization_status: LambdaM085RIntegratedDilocoAuthorizationStatus
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
    def _validate_authorization(self) -> LambdaM085RIntegratedDilocoAuthorization:
        if self.launch_ready or self.launch_allowed or self.run_now:
            raise ValueError("M085R authorization is future-only and cannot run now")
        if self.billable_action_performed:
            raise ValueError("M084A authorization package cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m085r_integrated_diloco_smoke"
            and self.blockers
        ):
            raise ValueError("authorized future M085R package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m085r_integrated_diloco_authorization_from_paths(
    *,
    readiness: str | Path,
    command_discovery: str | Path,
    policy: str | Path,
) -> LambdaM085RIntegratedDilocoAuthorization:
    ready = load_lambda_integrated_diloco_synthetic_readiness(readiness)
    discovery = load_lambda_integrated_diloco_command_discovery(command_discovery)
    integrated_policy = load_lambda_integrated_diloco_policy(policy)
    blockers: list[str] = []
    if ready.readiness_status != "ready_for_future_integrated_diloco_planning":
        blockers.append("integrated_diloco_readiness_not_ready")
    if discovery.discovery_status != "found_safe_integrated_diloco_command":
        blockers.append("no_safe_integrated_diloco_command_found")
    if integrated_policy.policy_status != "policy_passed":
        blockers.append("integrated_diloco_policy_not_passed")
    status: LambdaM085RIntegratedDilocoAuthorizationStatus = (
        "authorized_for_future_m085r_integrated_diloco_smoke"
        if not blockers
        else "not_authorized"
    )
    return LambdaM085RIntegratedDilocoAuthorization(
        authorization_status=status,
        command_category=discovery.command_category,
        blockers=blockers,
        warnings=[
            "authorization is future-only and still requires fresh discovery and "
            "operator approval",
        ],
    )


def load_lambda_m085r_integrated_diloco_authorization(
    path: str | Path,
) -> LambdaM085RIntegratedDilocoAuthorization:
    return LambdaM085RIntegratedDilocoAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m085r_integrated_diloco_authorization(
    path: str | Path,
    report: LambdaM085RIntegratedDilocoAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
