"""Future-only M051 Lambda remote bootstrap authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bootstrap_risk_review import (
    load_lambda_bootstrap_risk_review,
)
from decodilo.lambda_cloud.remote_bootstrap_scope import load_lambda_remote_bootstrap_scope

LambdaM051BootstrapAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m051_metadata_only_bootstrap_review",
    "authorized_for_future_m051_ssh_connectivity_review",
    "authorized_for_future_m051_single_allowlisted_command_review",
]


class LambdaM051BootstrapAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: LambdaM051BootstrapAuthorizationStatus
    selected_bootstrap_mode: str | None = None
    launch_authorized_now: bool = False
    future_review_authorized: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    ssh_execution_allowed_now: bool = False
    remote_command_execution_allowed_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaM051BootstrapAuthorization:
        if (
            self.launch_authorized_now
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.package_install_allowed
            or self.training_allowed
            or self.ssh_execution_allowed_now
            or self.remote_command_execution_allowed_now
        ):
            raise ValueError("M051 bootstrap authorization cannot execute now")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_bootstrap_authorization_from_paths(
    *,
    scope: str | Path,
    risk_review: str | Path,
) -> LambdaM051BootstrapAuthorization:
    scope_report = load_lambda_remote_bootstrap_scope(scope)
    risk = load_lambda_bootstrap_risk_review(risk_review)
    blockers = [*scope_report.blockers, *risk.blockers]
    if not risk.lifecycle_closeout_succeeded:
        blockers.append("lifecycle_smoke_closeout_required")
    if not risk.risk_review_passed:
        blockers.append("bootstrap_risk_review_not_passed")
    if scope_report.package_install_allowed:
        blockers.append("package_install_must_remain_denied")
    if scope_report.training_allowed:
        blockers.append("training_must_remain_denied")
    mode = risk.selected_bootstrap_mode
    status: LambdaM051BootstrapAuthorizationStatus = "not_authorized"
    if not blockers and mode == "lifecycle_plus_metadata_only":
        status = "authorized_for_future_m051_metadata_only_bootstrap_review"
    elif not blockers and mode == "lifecycle_plus_ssh_connectivity_check":
        status = "authorized_for_future_m051_ssh_connectivity_review"
    elif not blockers and mode == "lifecycle_plus_single_benign_command":
        status = "authorized_for_future_m051_single_allowlisted_command_review"
    return LambdaM051BootstrapAuthorization(
        authorization_status=status,
        selected_bootstrap_mode=mode if status != "not_authorized" else None,
        future_review_authorized=status != "not_authorized",
        blockers=sorted(set(blockers)),
        warnings=[
            "M051 authorization is future-review only",
            "M050 performs no launch, SSH, package install, or training",
            "M052 may close out a completed M051B run but cannot authorize execution",
            *risk.warnings,
        ],
    )


def load_lambda_m051_bootstrap_authorization(
    path: str | Path,
) -> LambdaM051BootstrapAuthorization:
    return LambdaM051BootstrapAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_bootstrap_authorization(
    path: str | Path,
    report: LambdaM051BootstrapAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
