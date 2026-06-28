"""Future-only authorization for an M075R2 runtime-smoke retry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_authorization import (
    load_lambda_m075r_runtime_protocol_smoke_authorization,
)
from decodilo.lambda_cloud.remote_vslice_failure_artifact_capture_policy import (
    load_lambda_remote_vslice_failure_artifact_capture_policy,
)
from decodilo.lambda_cloud.runtime_smoke_failure_closeout import (
    load_lambda_runtime_smoke_failure_closeout,
)

LambdaM075R2RuntimeSmokeRetryAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m075r2_runtime_smoke_retry",
]


class LambdaM075R2RuntimeSmokeRetryAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075S"
    authorization_status: LambdaM075R2RuntimeSmokeRetryAuthorizationStatus
    run_now: bool = False
    future_only: bool = True
    max_launch_attempts: int = 1
    max_source_bundle_uploads: int = 1
    max_dependency_bundle_uploads: int = 1
    capture_failure_artifact_required: bool = True
    requires_fresh_discovery: bool = True
    requires_fresh_operator_confirmation: bool = True
    no_immediate_launch: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_authorization(self) -> LambdaM075R2RuntimeSmokeRetryAuthorization:
        if self.run_now or self.launch_ready or self.launch_allowed:
            raise ValueError("M075R2 authorization must remain future-only")
        if self.billable_action_performed:
            raise ValueError("M075S cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m075r2_runtime_smoke_retry"
            and self.blockers
        ):
            raise ValueError("authorized M075R2 retry cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m075r2_runtime_smoke_retry_authorization_from_paths(
    *,
    failure_closeout: str | Path,
    failure_artifact_policy: str | Path,
    runtime_authorization: str | Path,
) -> LambdaM075R2RuntimeSmokeRetryAuthorization:
    closeout = load_lambda_runtime_smoke_failure_closeout(failure_closeout)
    capture = load_lambda_remote_vslice_failure_artifact_capture_policy(
        failure_artifact_policy
    )
    runtime_auth = load_lambda_m075r_runtime_protocol_smoke_authorization(
        runtime_authorization
    )
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("runtime_smoke_failure_closeout_not_succeeded")
    if closeout.closeout_status not in {
        "closed_runtime_smoke_command_failed_evidence_insufficient",
        "closed_runtime_smoke_command_failed_with_artifact_metadata",
    }:
        blockers.append("runtime_smoke_closeout_status_not_retryable")
    if not capture.policy_passed or not capture.capture_on_failure_allowed:
        blockers.append("failure_artifact_capture_policy_not_passed")
    if (
        runtime_auth.authorization_status
        != "authorized_for_future_m075r_runtime_protocol_smoke"
    ):
        blockers.append("m075r_runtime_authorization_not_valid")
    status: LambdaM075R2RuntimeSmokeRetryAuthorizationStatus = (
        "authorized_for_future_m075r2_runtime_smoke_retry"
        if not blockers
        else "not_authorized"
    )
    return LambdaM075R2RuntimeSmokeRetryAuthorization(
        authorization_status=status,
        blockers=sorted(set(blockers)),
        warnings=[
            "authorization is future-only",
            "M075R2 still requires fresh discovery and operator approval",
        ],
    )


def load_lambda_m075r2_runtime_smoke_retry_authorization(
    path: str | Path,
) -> LambdaM075R2RuntimeSmokeRetryAuthorization:
    return LambdaM075R2RuntimeSmokeRetryAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m075r2_runtime_smoke_retry_authorization(
    path: str | Path,
    report: LambdaM075R2RuntimeSmokeRetryAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
