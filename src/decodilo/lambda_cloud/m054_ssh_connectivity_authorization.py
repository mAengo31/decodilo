"""Future-only M054 SSH-connectivity authorization package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_connectivity_risk_review import (
    load_lambda_ssh_connectivity_risk_review,
)

LambdaM054SSHConnectivityAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m054_ssh_connectivity_review",
]


class LambdaM054SSHConnectivityAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: LambdaM054SSHConnectivityAuthorizationStatus
    future_review_authorized: bool = False
    launch_authorized_now: bool = False
    ssh_authorized_now: bool = False
    remote_command_authorized_now: bool = False
    file_transfer_authorized_now: bool = False
    port_forwarding_authorized_now: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaM054SSHConnectivityAuthorization:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.launch_authorized_now
            or self.ssh_authorized_now
            or self.remote_command_authorized_now
            or self.file_transfer_authorized_now
            or self.port_forwarding_authorized_now
            or self.package_install_allowed
            or self.training_allowed
        ):
            raise ValueError("M054 SSH authorization cannot execute now")
        if self.future_review_authorized and self.authorization_status == "not_authorized":
            raise ValueError("future review flag cannot be true when not authorized")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m054_ssh_connectivity_authorization_from_path(
    risk_review: str | Path,
) -> LambdaM054SSHConnectivityAuthorization:
    risk = load_lambda_ssh_connectivity_risk_review(risk_review)
    blockers = list(risk.blockers)
    if risk.risk_review_status == "planning_incomplete":
        if risk.operator_approval_status == "declined":
            blockers.append("operator_approval_declined")
        else:
            blockers.append("operator_approval_not_provided")
    elif not risk.risk_review_passed:
        blockers.append("ssh_connectivity_risk_review_not_passed")
    status: LambdaM054SSHConnectivityAuthorizationStatus = (
        "authorized_for_future_m054_ssh_connectivity_review" if not blockers else "not_authorized"
    )
    return LambdaM054SSHConnectivityAuthorization(
        authorization_status=status,
        future_review_authorized=status != "not_authorized",
        blockers=sorted(set(blockers)),
        warnings=[
            "M054 authorization is future-review only",
            (
                "SSH, launch, commands, file transfer, forwarding, install, "
                "and training remain unauthorized now"
            ),
            *risk.warnings,
        ],
    )


def load_lambda_m054_ssh_connectivity_authorization(
    path: str | Path,
) -> LambdaM054SSHConnectivityAuthorization:
    return LambdaM054SSHConnectivityAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m054_ssh_connectivity_authorization(
    path: str | Path,
    report: LambdaM054SSHConnectivityAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
