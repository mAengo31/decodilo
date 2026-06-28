"""Future-only M083R bounded DiLoCo optimizer-fidelity authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_optimizer_command_discovery import (
    load_lambda_diloco_optimizer_command_discovery,
)
from decodilo.lambda_cloud.diloco_optimizer_policy import (
    load_lambda_diloco_optimizer_policy,
)
from decodilo.lambda_cloud.diloco_optimizer_readiness import (
    load_lambda_diloco_optimizer_readiness,
)
from decodilo.lambda_cloud.diloco_synthetic_closeout import (
    load_lambda_diloco_synthetic_closeout,
)

LambdaM083RDilocoOptimizerAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m083r_diloco_optimizer_smoke",
]


class LambdaM083RDilocoOptimizerAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M082A"
    authorization_status: LambdaM083RDilocoOptimizerAuthorizationStatus
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
    def _validate_authorization(self) -> LambdaM083RDilocoOptimizerAuthorization:
        if self.launch_ready or self.launch_allowed or self.run_now:
            raise ValueError("M083R authorization is future-only and cannot run now")
        if self.billable_action_performed:
            raise ValueError("M082 authorization package cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m083r_diloco_optimizer_smoke"
            and self.blockers
        ):
            raise ValueError("authorized future M083R package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m083r_diloco_optimizer_authorization_from_paths(
    *,
    diloco_synthetic_closeout: str | Path,
    readiness: str | Path,
    command_discovery: str | Path,
    policy: str | Path,
) -> LambdaM083RDilocoOptimizerAuthorization:
    closeout = load_lambda_diloco_synthetic_closeout(diloco_synthetic_closeout)
    ready = load_lambda_diloco_optimizer_readiness(readiness)
    discovery = load_lambda_diloco_optimizer_command_discovery(command_discovery)
    optimizer_policy = load_lambda_diloco_optimizer_policy(policy)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("diloco_synthetic_closeout_not_succeeded")
    if ready.readiness_status != "ready_for_future_diloco_optimizer_planning":
        blockers.append("diloco_optimizer_readiness_not_ready")
    if discovery.discovery_status != "found_safe_diloco_optimizer_command":
        blockers.append("no_safe_diloco_optimizer_command_found")
    if optimizer_policy.policy_status != "policy_passed":
        blockers.append("diloco_optimizer_policy_not_passed")
    status: LambdaM083RDilocoOptimizerAuthorizationStatus = (
        "authorized_for_future_m083r_diloco_optimizer_smoke"
        if not blockers
        else "not_authorized"
    )
    return LambdaM083RDilocoOptimizerAuthorization(
        authorization_status=status,
        command_category=discovery.command_category,
        blockers=blockers,
        warnings=[
            "authorization is future-only and still requires fresh discovery and "
            "operator approval",
        ],
    )


def load_lambda_m083r_diloco_optimizer_authorization(
    path: str | Path,
) -> LambdaM083RDilocoOptimizerAuthorization:
    return LambdaM083RDilocoOptimizerAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m083r_diloco_optimizer_authorization(
    path: str | Path,
    report: LambdaM083RDilocoOptimizerAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
