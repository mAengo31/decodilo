"""Future-only M081R2 retry authorization after manifest artifact capture fix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_artifact_parser import (
    DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.diloco_smoke_attempt_closeout import (
    load_lambda_diloco_smoke_attempt_closeout,
)
from decodilo.lambda_cloud.m081r_diloco_synthetic_authorization import (
    load_lambda_m081r_diloco_synthetic_authorization,
)
from decodilo.lambda_cloud.remote_vslice_manifest_artifact_capture import (
    load_lambda_remote_vslice_manifest_artifact_policy,
)

LambdaM081R2DilocoSyntheticAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m081r2_diloco_synthetic_retry",
]


class LambdaM081R2DilocoSyntheticAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M081S"
    authorization_status: LambdaM081R2DilocoSyntheticAuthorizationStatus
    reason: str
    run_now: bool = False
    future_only: bool = True
    declared_artifact_path: str = DILOCO_SMOKE_DECLARED_ARTIFACT_PATH
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
    def _validate_authorization(self) -> LambdaM081R2DilocoSyntheticAuthorization:
        if self.run_now or self.launch_ready or self.launch_allowed:
            raise ValueError("M081R2 authorization must remain future-only")
        if self.billable_action_performed:
            raise ValueError("M081S authorization cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m081r2_diloco_synthetic_retry"
            and self.blockers
        ):
            raise ValueError("authorized M081R2 retry cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m081r2_diloco_synthetic_authorization_from_paths(
    *,
    attempt_closeout: str | Path,
    manifest_artifact_policy: str | Path,
    previous_authorization: str | Path,
) -> LambdaM081R2DilocoSyntheticAuthorization:
    closeout = load_lambda_diloco_smoke_attempt_closeout(attempt_closeout)
    policy = load_lambda_remote_vslice_manifest_artifact_policy(manifest_artifact_policy)
    previous = load_lambda_m081r_diloco_synthetic_authorization(
        previous_authorization
    )
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("m081r_attempt_closeout_not_succeeded")
    if (
        closeout.closeout_status
        != "closed_diloco_smoke_command_passed_artifact_capture_blocked"
    ):
        blockers.append("m081r_closeout_status_not_retryable")
    if not closeout.diloco_smoke_command_passed:
        blockers.append("diloco_smoke_command_not_passed")
    if policy.policy_status != "manifest_artifact_policy_defined":
        blockers.extend(policy.blockers or ["manifest_artifact_policy_not_defined"])
    if policy.declared_artifact_path != DILOCO_SMOKE_DECLARED_ARTIFACT_PATH:
        blockers.append("diloco_declared_artifact_path_missing")
    if not policy.diloco_smoke_declared_artifact_supported:
        blockers.append("diloco_declared_artifact_not_supported")
    if (
        previous.authorization_status
        != "authorized_for_future_m081r_diloco_synthetic_experiment"
    ):
        blockers.append("previous_m081r_authorization_not_valid")
    status: LambdaM081R2DilocoSyntheticAuthorizationStatus = (
        "authorized_for_future_m081r2_diloco_synthetic_retry"
        if not blockers
        else "not_authorized"
    )
    return LambdaM081R2DilocoSyntheticAuthorization(
        authorization_status=status,
        reason=(
            "retry_with_manifest_declared_diloco_artifact_capture_fixed"
            if not blockers
            else "blocked"
        ),
        blockers=sorted(set(blockers)),
        warnings=[
            "authorization is future-only",
            "M081R2 still requires fresh discovery and supervised approval",
        ],
    )


def load_lambda_m081r2_diloco_synthetic_authorization(
    path: str | Path,
) -> LambdaM081R2DilocoSyntheticAuthorization:
    return LambdaM081R2DilocoSyntheticAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m081r2_diloco_synthetic_authorization(
    path: str | Path,
    authorization: LambdaM081R2DilocoSyntheticAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(authorization.to_json(), encoding="utf-8")
