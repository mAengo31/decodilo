"""Future-only M081R bounded DiLoCo-shaped synthetic experiment authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_synthetic_command_discovery import (
    load_lambda_diloco_synthetic_command_discovery,
)
from decodilo.lambda_cloud.diloco_synthetic_policy import (
    load_lambda_diloco_synthetic_policy,
)
from decodilo.lambda_cloud.diloco_synthetic_readiness import (
    load_lambda_diloco_synthetic_readiness,
)
from decodilo.lambda_cloud.learner_syncer_smoke_closeout import (
    load_lambda_learner_syncer_smoke_closeout,
)

LambdaM081RDilocoSyntheticAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m081r_diloco_synthetic_experiment",
]


class LambdaM081RDilocoSyntheticAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M080"
    authorization_status: LambdaM081RDilocoSyntheticAuthorizationStatus
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
    def _validate_authorization(self) -> LambdaM081RDilocoSyntheticAuthorization:
        if self.launch_ready or self.launch_allowed or self.run_now:
            raise ValueError("M081R authorization is future-only and cannot run now")
        if self.billable_action_performed:
            raise ValueError("M080 authorization package cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m081r_diloco_synthetic_experiment"
            and self.blockers
        ):
            raise ValueError("authorized future M081R package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m081r_diloco_synthetic_authorization_from_paths(
    *,
    learner_syncer_closeout: str | Path,
    readiness: str | Path,
    command_discovery: str | Path,
    policy: str | Path,
) -> LambdaM081RDilocoSyntheticAuthorization:
    closeout = load_lambda_learner_syncer_smoke_closeout(learner_syncer_closeout)
    ready = load_lambda_diloco_synthetic_readiness(readiness)
    discovery = load_lambda_diloco_synthetic_command_discovery(command_discovery)
    experiment_policy = load_lambda_diloco_synthetic_policy(policy)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("learner_syncer_smoke_closeout_not_succeeded")
    if ready.readiness_status != "ready_for_future_diloco_synthetic_planning":
        blockers.append("diloco_synthetic_readiness_not_ready")
    if discovery.discovery_status != "found_safe_diloco_synthetic_command":
        blockers.append("no_safe_diloco_synthetic_command_found")
    if experiment_policy.policy_status != "policy_passed":
        blockers.append("diloco_synthetic_policy_not_passed")
    status: LambdaM081RDilocoSyntheticAuthorizationStatus = (
        "authorized_for_future_m081r_diloco_synthetic_experiment"
        if not blockers
        else "not_authorized"
    )
    return LambdaM081RDilocoSyntheticAuthorization(
        authorization_status=status,
        command_category=discovery.command_category,
        blockers=blockers,
        warnings=[
            "authorization is future-only and still requires fresh discovery and "
            "operator approval",
        ],
    )


def load_lambda_m081r_diloco_synthetic_authorization(
    path: str | Path,
) -> LambdaM081RDilocoSyntheticAuthorization:
    return LambdaM081RDilocoSyntheticAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m081r_diloco_synthetic_authorization(
    path: str | Path,
    report: LambdaM081RDilocoSyntheticAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
