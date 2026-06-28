"""Future-only M087R bounded parameter-fragment synthetic authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.parameter_fragment_command_discovery import (
    load_lambda_parameter_fragment_command_discovery,
)
from decodilo.lambda_cloud.parameter_fragment_policy import (
    load_lambda_parameter_fragment_policy,
)
from decodilo.lambda_cloud.parameter_fragment_readiness import (
    load_lambda_parameter_fragment_readiness,
)

LambdaM087RParameterFragmentAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m087r_parameter_fragment_smoke",
]


class LambdaM087RParameterFragmentAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M086A"
    authorization_status: LambdaM087RParameterFragmentAuthorizationStatus
    run_now: bool = False
    future_only: bool = True
    command_category: str | None = None
    max_launch_attempts: int = 1
    max_instances: int = 1
    halt_after_first_failed_live_stage: bool = True
    no_internet_install: bool = True
    no_downloads: bool = True
    no_real_training: bool = True
    expected_parameter_fragment_semantics: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_authorization(self) -> LambdaM087RParameterFragmentAuthorization:
        if self.launch_ready or self.launch_allowed or self.run_now:
            raise ValueError("M087R authorization is future-only and cannot run now")
        if self.billable_action_performed:
            raise ValueError("M086 authorization package cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m087r_parameter_fragment_smoke"
            and self.blockers
        ):
            raise ValueError("authorized future M087R package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m087r_parameter_fragment_authorization_from_paths(
    *,
    readiness: str | Path,
    command_discovery: str | Path,
    policy: str | Path,
) -> LambdaM087RParameterFragmentAuthorization:
    ready = load_lambda_parameter_fragment_readiness(readiness)
    discovery = load_lambda_parameter_fragment_command_discovery(command_discovery)
    fragment_policy = load_lambda_parameter_fragment_policy(policy)
    blockers: list[str] = []
    if ready.readiness_status != "ready_for_future_parameter_fragment_planning":
        blockers.append("parameter_fragment_readiness_not_ready")
    if discovery.discovery_status != "found_safe_parameter_fragment_command":
        blockers.append("no_safe_parameter_fragment_command_found")
    if discovery.expected_parameter_fragment_semantics != "synthetic_vector_fragments":
        blockers.append("parameter_fragment_smoke_not_verified")
    if fragment_policy.policy_status != "policy_passed":
        blockers.append("parameter_fragment_policy_not_passed")
    status: LambdaM087RParameterFragmentAuthorizationStatus = (
        "authorized_for_future_m087r_parameter_fragment_smoke"
        if not blockers
        else "not_authorized"
    )
    return LambdaM087RParameterFragmentAuthorization(
        authorization_status=status,
        command_category=discovery.command_category,
        expected_parameter_fragment_semantics=(
            discovery.expected_parameter_fragment_semantics
        ),
        blockers=blockers,
        warnings=[
            "authorization is future-only and still requires fresh discovery and "
            "operator approval",
        ],
    )


def load_lambda_m087r_parameter_fragment_authorization(
    path: str | Path,
) -> LambdaM087RParameterFragmentAuthorization:
    return LambdaM087RParameterFragmentAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m087r_parameter_fragment_authorization(
    path: str | Path,
    report: LambdaM087RParameterFragmentAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
