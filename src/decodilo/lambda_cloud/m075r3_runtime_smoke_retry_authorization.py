"""Future-only M075R3 authorization for runtime-smoke retry with body capture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m075r2_runtime_smoke_retry_authorization import (
    load_lambda_m075r2_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_body_policy import (
    load_lambda_runtime_smoke_artifact_body_policy,
)
from decodilo.lambda_cloud.runtime_smoke_attempt_closeout import (
    load_lambda_runtime_smoke_attempt_closeout,
)

LambdaM075R3RuntimeSmokeRetryAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m075r3_runtime_smoke_retry",
]


class LambdaM075R3RuntimeSmokeRetryAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075T"
    authorization_status: LambdaM075R3RuntimeSmokeRetryAuthorizationStatus
    reason: str
    run_now: bool = False
    future_only: bool = True
    body_or_summary_capture_required: bool = True
    max_launch_attempts: int = 1
    max_source_bundle_uploads: int = 1
    max_dependency_bundle_uploads: int = 1
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_authorization(self) -> LambdaM075R3RuntimeSmokeRetryAuthorization:
        if self.run_now or self.launch_ready or self.launch_allowed:
            raise ValueError("M075R3 authorization must remain future-only")
        if self.billable_action_performed:
            raise ValueError("M075T authorization cannot spend money")
        if (
            self.authorization_status == "authorized_for_future_m075r3_runtime_smoke_retry"
            and self.blockers
        ):
            raise ValueError("authorized M075R3 retry cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m075r3_runtime_smoke_retry_authorization_from_paths(
    *,
    attempt_closeout: str | Path,
    artifact_body_policy: str | Path,
    previous_authorization: str | Path,
) -> LambdaM075R3RuntimeSmokeRetryAuthorization:
    closeout = load_lambda_runtime_smoke_attempt_closeout(attempt_closeout)
    body_policy = load_lambda_runtime_smoke_artifact_body_policy(artifact_body_policy)
    previous = load_lambda_m075r2_runtime_smoke_retry_authorization(
        previous_authorization
    )
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("m075r2_attempt_closeout_not_succeeded")
    if (
        closeout.closeout_status
        != "closed_runtime_smoke_command_failed_with_artifact_metadata_captured"
    ):
        blockers.append("m075r2_closeout_status_not_retryable")
    if body_policy.policy_status != "policy_defined":
        blockers.extend(body_policy.blockers or ["artifact_body_policy_not_defined"])
    if not body_policy.content_capture_allowed:
        blockers.append("artifact_body_capture_not_allowed")
    if (
        previous.authorization_status
        != "authorized_for_future_m075r2_runtime_smoke_retry"
    ):
        blockers.append("previous_m075r2_authorization_not_valid")
    status: LambdaM075R3RuntimeSmokeRetryAuthorizationStatus = (
        "authorized_for_future_m075r3_runtime_smoke_retry"
        if not blockers
        else "not_authorized"
    )
    return LambdaM075R3RuntimeSmokeRetryAuthorization(
        authorization_status=status,
        reason=(
            "retry_with_declared_artifact_body_or_summary_capture"
            if not blockers
            else "blocked"
        ),
        blockers=sorted(set(blockers)),
        warnings=[
            "authorization is future-only",
            "M075R3 still requires fresh discovery and operator approval",
        ],
    )


def load_lambda_m075r3_runtime_smoke_retry_authorization(
    path: str | Path,
) -> LambdaM075R3RuntimeSmokeRetryAuthorization:
    return LambdaM075R3RuntimeSmokeRetryAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m075r3_runtime_smoke_retry_authorization(
    path: str | Path,
    authorization: LambdaM075R3RuntimeSmokeRetryAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(authorization.to_json(), encoding="utf-8")
