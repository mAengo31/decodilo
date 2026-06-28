"""Future-only M073R tiny Decodilo smoke authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.first_experiment_closeout import (
    load_lambda_first_experiment_closeout,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_discovery import (
    load_lambda_tiny_decodilo_smoke_discovery,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_policy import (
    load_lambda_tiny_decodilo_smoke_policy,
)

LambdaM073RTinySmokeAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m073r_tiny_decodilo_smoke",
]


class LambdaM073RTinySmokeAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M072"
    authorization_status: LambdaM073RTinySmokeAuthorizationStatus
    run_now: bool = False
    future_only: bool = True
    command_category: str | None = None
    max_launch_attempts: int = 1
    max_instances: int = 1
    stop_on_first_failure: bool = True
    no_internet_install: bool = True
    no_downloads: bool = True
    no_training: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_authorization(self) -> LambdaM073RTinySmokeAuthorization:
        if self.launch_ready or self.launch_allowed or self.run_now:
            raise ValueError("M073R authorization is future-only and cannot run now")
        if self.billable_action_performed:
            raise ValueError("M072 authorization package cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m073r_tiny_decodilo_smoke"
            and self.blockers
        ):
            raise ValueError("authorized future M073R package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m073r_tiny_smoke_authorization_from_paths(
    *,
    first_experiment_closeout: str | Path,
    command_discovery: str | Path,
    policy: str | Path,
) -> LambdaM073RTinySmokeAuthorization:
    closeout = load_lambda_first_experiment_closeout(first_experiment_closeout)
    discovery = load_lambda_tiny_decodilo_smoke_discovery(command_discovery)
    smoke_policy = load_lambda_tiny_decodilo_smoke_policy(policy)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("first_experiment_closeout_not_succeeded")
    if discovery.discovery_status not in {
        "found_safe_tiny_smoke_command",
        "safe_tiny_smoke_command_found",
    }:
        blockers.append("no_safe_tiny_smoke_command_found")
    if smoke_policy.policy_status != "policy_passed":
        blockers.append("tiny_smoke_policy_not_passed")
    status: LambdaM073RTinySmokeAuthorizationStatus = (
        "authorized_for_future_m073r_tiny_decodilo_smoke"
        if not blockers
        else "not_authorized"
    )
    return LambdaM073RTinySmokeAuthorization(
        authorization_status=status,
        command_category=discovery.command_category,
        blockers=blockers,
        warnings=[
            "authorization is future-only and still requires fresh discovery and operator approval",
        ],
    )


def load_lambda_m073r_tiny_smoke_authorization(
    path: str | Path,
) -> LambdaM073RTinySmokeAuthorization:
    return LambdaM073RTinySmokeAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m073r_tiny_smoke_authorization(
    path: str | Path,
    report: LambdaM073RTinySmokeAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
