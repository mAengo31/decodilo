"""Future-only authorization for an M073R2 tiny-smoke retry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m073r_tiny_smoke_authorization import (
    load_lambda_m073r_tiny_smoke_authorization,
)
from decodilo.lambda_cloud.remote_vslice_upload_closeout import (
    load_lambda_remote_vslice_upload_closeout,
)
from decodilo.lambda_cloud.source_bundle_upload_policy import (
    load_lambda_source_dependency_upload_policy,
)

LambdaM073R2RetryAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m073r2_tiny_smoke_retry",
]


class LambdaM073R2RetryAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M073S"
    authorization_status: LambdaM073R2RetryAuthorizationStatus
    run_now: bool = False
    future_only: bool = True
    max_launch_attempts: int = 1
    max_source_bundle_uploads: int = 1
    max_dependency_bundle_uploads: int = 1
    requires_ssh_banner_readiness: bool = True
    requires_fresh_discovery: bool = True
    requires_fresh_operator_confirmation: bool = True
    no_immediate_launch: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_authorization(self) -> LambdaM073R2RetryAuthorization:
        if self.run_now or self.launch_ready or self.launch_allowed:
            raise ValueError("M073R2 authorization must remain future-only")
        if self.billable_action_performed:
            raise ValueError("M073S cannot spend money")
        if (
            self.authorization_status
            == "authorized_for_future_m073r2_tiny_smoke_retry"
            and self.blockers
        ):
            raise ValueError("authorized M073R2 retry cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m073r2_retry_authorization_from_paths(
    *,
    upload_closeout: str | Path,
    upload_policy: str | Path,
    tiny_smoke_authorization: str | Path,
) -> LambdaM073R2RetryAuthorization:
    closeout = load_lambda_remote_vslice_upload_closeout(upload_closeout)
    policy = load_lambda_source_dependency_upload_policy(upload_policy)
    tiny_auth = load_lambda_m073r_tiny_smoke_authorization(tiny_smoke_authorization)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("upload_closeout_not_succeeded")
    if closeout.closeout_status not in {
        "closed_source_upload_ssh_banner_timeout",
        "closed_source_upload_connection_closed",
    }:
        blockers.append("upload_closeout_not_pre_manifest_readiness_failure")
    if policy.upload_policy_status != "policy_defined":
        blockers.append("upload_policy_not_defined")
    if not policy.upload_only_after_ssh_banner_readiness:
        blockers.append("banner_readiness_not_required_before_upload")
    if tiny_auth.authorization_status != "authorized_for_future_m073r_tiny_decodilo_smoke":
        blockers.append("tiny_smoke_not_authorized")
    status: LambdaM073R2RetryAuthorizationStatus = (
        "authorized_for_future_m073r2_tiny_smoke_retry"
        if not blockers
        else "not_authorized"
    )
    return LambdaM073R2RetryAuthorization(
        authorization_status=status,
        blockers=blockers,
        warnings=[
            (
                "authorization is future-only; M073R2 still requires fresh discovery "
                "and operator approval"
            ),
        ],
    )


def load_lambda_m073r2_retry_authorization(
    path: str | Path,
) -> LambdaM073R2RetryAuthorization:
    return LambdaM073R2RetryAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m073r2_retry_authorization(
    path: str | Path,
    report: LambdaM073R2RetryAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
