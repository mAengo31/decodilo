"""Future-only M075R4 authorization after local update-stream fix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.dev.runtime_smoke import load_runtime_smoke_report
from decodilo.lambda_cloud.runtime_smoke_update_stream_closeout import (
    load_lambda_runtime_smoke_update_stream_closeout,
)
from decodilo.lambda_cloud.runtime_smoke_update_stream_diagnostic import (
    load_lambda_runtime_smoke_update_stream_diagnostic,
)

LambdaM075R4RuntimeSmokeRetryAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m075r4_runtime_smoke_retry",
]


class LambdaM075R4RuntimeSmokeRetryAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075U"
    authorization_status: LambdaM075R4RuntimeSmokeRetryAuthorizationStatus
    reason: str
    run_now: bool = False
    future_only: bool = True
    local_update_stream_fix_verified: bool
    local_after_runtime_smoke_status: str | None = None
    max_launch_attempts: int = 1
    max_source_bundle_uploads: int = 1
    max_dependency_bundle_uploads: int = 1
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_authorization(self) -> LambdaM075R4RuntimeSmokeRetryAuthorization:
        if self.run_now or self.launch_ready or self.launch_allowed:
            raise ValueError("M075R4 authorization must remain future-only")
        if self.billable_action_performed:
            raise ValueError("M075U authorization cannot spend money")
        if (
            self.authorization_status == "authorized_for_future_m075r4_runtime_smoke_retry"
            and self.blockers
        ):
            raise ValueError("authorized M075R4 retry cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m075r4_runtime_smoke_retry_authorization_from_paths(
    *,
    update_stream_closeout: str | Path,
    diagnostic: str | Path,
    local_after_report: str | Path,
) -> LambdaM075R4RuntimeSmokeRetryAuthorization:
    closeout = load_lambda_runtime_smoke_update_stream_closeout(
        update_stream_closeout
    )
    diag = load_lambda_runtime_smoke_update_stream_diagnostic(diagnostic)
    local_after = load_runtime_smoke_report(local_after_report)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("update_stream_closeout_not_succeeded")
    if closeout.closeout_status != "closed_runtime_smoke_update_stream_timeout":
        blockers.append("update_stream_closeout_status_not_retryable")
    if diag.diagnostic_status != "diagnosed_update_stream_timeout_path":
        blockers.append("update_stream_diagnostic_not_passed")
    if local_after.runtime_smoke_status != "passed":
        blockers.append("local_update_stream_fix_not_verified")
    if local_after.protocol_or_event_check_passed is not True:
        blockers.append("local_protocol_or_event_check_not_passed")
    if local_after.launch_ready or local_after.launch_allowed:
        blockers.append("local_after_report_enabled_launch")
    status: LambdaM075R4RuntimeSmokeRetryAuthorizationStatus = (
        "authorized_for_future_m075r4_runtime_smoke_retry"
        if not blockers
        else "not_authorized"
    )
    return LambdaM075R4RuntimeSmokeRetryAuthorization(
        authorization_status=status,
        reason="local_update_stream_fix_verified" if not blockers else "blocked",
        local_update_stream_fix_verified=not blockers,
        local_after_runtime_smoke_status=local_after.runtime_smoke_status,
        blockers=sorted(set(blockers)),
        warnings=[
            "authorization is future-only",
            "M075R4 still requires fresh discovery and explicit supervised approval",
        ],
    )


def load_lambda_m075r4_runtime_smoke_retry_authorization(
    path: str | Path,
) -> LambdaM075R4RuntimeSmokeRetryAuthorization:
    return LambdaM075R4RuntimeSmokeRetryAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m075r4_runtime_smoke_retry_authorization(
    path: str | Path,
    authorization: LambdaM075R4RuntimeSmokeRetryAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(authorization.to_json(), encoding="utf-8")
