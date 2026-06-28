"""Future-only M075R runtime/protocol smoke authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.runtime_protocol_smoke_discovery import (
    load_lambda_runtime_protocol_smoke_discovery,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_policy import (
    load_lambda_runtime_protocol_smoke_policy,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_readiness import (
    load_lambda_runtime_protocol_smoke_readiness,
)
from decodilo.lambda_cloud.tiny_smoke_closeout import load_lambda_tiny_smoke_closeout

LambdaM075RRuntimeProtocolSmokeAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m075r_runtime_protocol_smoke",
]


class LambdaM075RRuntimeProtocolSmokeAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M074"
    authorization_status: LambdaM075RRuntimeProtocolSmokeAuthorizationStatus
    run_now: bool = False
    future_only: bool = True
    command_category: str | None = None
    max_launch_attempts: int = 1
    max_instances: int = 1
    stop_on_first_failure: bool = True
    no_internet_install: bool = True
    no_downloads: bool = True
    no_real_training: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_authorization(self) -> LambdaM075RRuntimeProtocolSmokeAuthorization:
        if self.launch_ready or self.launch_allowed or self.run_now:
            raise ValueError("M075R authorization is future-only and cannot run now")
        if self.billable_action_performed:
            raise ValueError("M074 authorization package cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m075r_runtime_protocol_smoke"
            and self.blockers
        ):
            raise ValueError("authorized future M075R package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m075r_runtime_protocol_smoke_authorization_from_paths(
    *,
    tiny_smoke_closeout: str | Path,
    readiness: str | Path,
    command_discovery: str | Path,
    policy: str | Path,
) -> LambdaM075RRuntimeProtocolSmokeAuthorization:
    closeout = load_lambda_tiny_smoke_closeout(tiny_smoke_closeout)
    ready = load_lambda_runtime_protocol_smoke_readiness(readiness)
    discovery = load_lambda_runtime_protocol_smoke_discovery(command_discovery)
    smoke_policy = load_lambda_runtime_protocol_smoke_policy(policy)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("tiny_smoke_closeout_not_succeeded")
    if ready.readiness_status != "ready_for_future_runtime_protocol_smoke_planning":
        blockers.append("runtime_protocol_smoke_readiness_not_ready")
    if discovery.discovery_status != "found_safe_runtime_protocol_smoke_command":
        blockers.append("no_safe_runtime_protocol_smoke_command_found")
    if smoke_policy.policy_status != "policy_passed":
        blockers.append("runtime_protocol_smoke_policy_not_passed")
    status: LambdaM075RRuntimeProtocolSmokeAuthorizationStatus = (
        "authorized_for_future_m075r_runtime_protocol_smoke"
        if not blockers
        else "not_authorized"
    )
    return LambdaM075RRuntimeProtocolSmokeAuthorization(
        authorization_status=status,
        command_category=discovery.command_category,
        blockers=blockers,
        warnings=[
            "authorization is future-only and still requires fresh discovery and operator approval",
        ],
    )


def load_lambda_m075r_runtime_protocol_smoke_authorization(
    path: str | Path,
) -> LambdaM075RRuntimeProtocolSmokeAuthorization:
    return LambdaM075RRuntimeProtocolSmokeAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m075r_runtime_protocol_smoke_authorization(
    path: str | Path,
    report: LambdaM075RRuntimeProtocolSmokeAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
