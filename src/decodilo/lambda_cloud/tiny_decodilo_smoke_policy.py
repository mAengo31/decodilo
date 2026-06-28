"""Future tiny Decodilo smoke safety policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.tiny_decodilo_smoke_discovery import (
    load_lambda_tiny_decodilo_smoke_discovery,
)

LambdaTinyDecodiloSmokePolicyStatus = Literal[
    "policy_passed",
    "blocked_no_safe_command",
]


class LambdaTinyDecodiloSmokePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M072"
    policy_status: LambdaTinyDecodiloSmokePolicyStatus
    one_instance: bool = True
    source_bundle_required: bool = True
    dependency_bundle_required: bool = True
    local_only_dependency_install: bool = True
    one_tiny_decodilo_smoke_command: bool
    bounded_timeout: bool
    bounded_output: bool
    no_internet: bool = True
    no_model_or_data_download: bool = True
    no_package_install_beyond_local_wheelhouse: bool = True
    no_long_training: bool = True
    no_background_process: bool = True
    stop_on_first_failure: bool = True
    terminate_and_verify: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaTinyDecodiloSmokePolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("tiny smoke policy must remain future-only")
        if self.policy_status == "policy_passed" and self.blockers:
            raise ValueError("passing tiny smoke policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_tiny_decodilo_smoke_policy_from_path(
    *,
    command_discovery: str | Path,
) -> LambdaTinyDecodiloSmokePolicy:
    discovery = load_lambda_tiny_decodilo_smoke_discovery(command_discovery)
    safe = discovery.discovery_status in {
        "found_safe_tiny_smoke_command",
        "safe_tiny_smoke_command_found",
    }
    blockers = [] if safe else ["no_safe_tiny_smoke_command_found"]
    return LambdaTinyDecodiloSmokePolicy(
        policy_status="policy_passed" if safe else "blocked_no_safe_command",
        one_tiny_decodilo_smoke_command=safe,
        bounded_timeout=safe and discovery.timeout_seconds is not None,
        bounded_output=safe,
        blockers=blockers,
        warnings=[
            "policy is future-only; M073R requires a separate fresh operator confirmation",
        ],
    )


def load_lambda_tiny_decodilo_smoke_policy(path: str | Path) -> LambdaTinyDecodiloSmokePolicy:
    return LambdaTinyDecodiloSmokePolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_tiny_decodilo_smoke_policy(
    path: str | Path,
    report: LambdaTinyDecodiloSmokePolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
