"""Future-only M071R first experiment authorization package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.first_experiment_command_discovery import (
    load_lambda_first_experiment_command_discovery,
)
from decodilo.lambda_cloud.first_experiment_manifest import (
    load_lambda_first_experiment_manifest,
)
from decodilo.lambda_cloud.first_experiment_readiness import (
    load_lambda_first_experiment_readiness,
)

LambdaM071RFirstExperimentAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m071r_first_experiment_attempt",
]


class LambdaM071RFirstExperimentAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M070"
    authorization_status: LambdaM071RFirstExperimentAuthorizationStatus
    run_now: bool = False
    future_only: bool = True
    first_experiment_command_category: str | None = None
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
    def _validate_authorization(self) -> LambdaM071RFirstExperimentAuthorization:
        if self.launch_ready or self.launch_allowed or self.run_now:
            raise ValueError("M071R authorization is future-only and cannot run now")
        if self.billable_action_performed:
            raise ValueError("M070 authorization package cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m071r_first_experiment_attempt"
            and self.blockers
        ):
            raise ValueError("authorized future M071R package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m071r_first_experiment_authorization_from_paths(
    *,
    readiness: str | Path,
    command_discovery: str | Path,
    manifest: str | Path,
) -> LambdaM071RFirstExperimentAuthorization:
    ready = load_lambda_first_experiment_readiness(readiness)
    discovery = load_lambda_first_experiment_command_discovery(command_discovery)
    manifest_report = load_lambda_first_experiment_manifest(manifest)
    blockers: list[str] = []
    if ready.readiness_status != "ready_for_future_first_experiment_planning":
        blockers.append("first_experiment_readiness_not_ready")
    if discovery.discovery_status != "safe_experiment_command_found":
        blockers.append("no_safe_experiment_command_found")
    if manifest_report.manifest_status != "manifest_ready_for_future_review":
        blockers.append("first_experiment_manifest_not_ready")
    status: LambdaM071RFirstExperimentAuthorizationStatus = (
        "authorized_for_future_m071r_first_experiment_attempt"
        if not blockers
        else "not_authorized"
    )
    return LambdaM071RFirstExperimentAuthorization(
        authorization_status=status,
        first_experiment_command_category=discovery.command_category,
        blockers=blockers,
        warnings=[
            "authorization is future-only and still requires fresh discovery and operator approval",
        ],
    )


def load_lambda_m071r_first_experiment_authorization(
    path: str | Path,
) -> LambdaM071RFirstExperimentAuthorization:
    return LambdaM071RFirstExperimentAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m071r_first_experiment_authorization(
    path: str | Path,
    report: LambdaM071RFirstExperimentAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
