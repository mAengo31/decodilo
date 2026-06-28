"""Future-only M061 whoami identity-command authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m060_report import load_lambda_m060_report
from decodilo.lambda_cloud.m061_next_step_decision import (
    load_lambda_m061_next_step_decision,
)
from decodilo.lambda_cloud.ssh_hostname_identity_closeout import (
    load_lambda_ssh_hostname_identity_closeout,
)

LambdaM061WhoamiAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m061_whoami_identity_command_review",
]


class LambdaM061WhoamiAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: LambdaM061WhoamiAuthorizationStatus
    selected_future_command_set: list[str] = Field(default_factory=list)
    future_review_only: bool = True
    launch_authorized_now: bool = False
    command_authorized_now: bool = False
    gpu_visibility_authorized_now: bool = False
    python_authorized_now: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaM061WhoamiAuthorization:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.launch_authorized_now
            or self.command_authorized_now
            or self.gpu_visibility_authorized_now
            or self.python_authorized_now
            or self.package_install_allowed
            or self.training_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
        ):
            raise ValueError("M061 authorization cannot authorize immediate execution")
        if self.authorization_status == (
            "authorized_for_future_m061_whoami_identity_command_review"
        ):
            if self.blockers or self.selected_future_command_set != ["whoami"]:
                raise ValueError("M061 authorization requires exactly whoami")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m061_whoami_authorization_from_paths(
    *,
    m060_report: str | Path,
    hostname_closeout: str | Path,
    decision: str | Path,
) -> LambdaM061WhoamiAuthorization:
    report = load_lambda_m060_report(m060_report)
    closeout = load_lambda_ssh_hostname_identity_closeout(hostname_closeout)
    next_decision = load_lambda_m061_next_step_decision(decision)
    blockers = [*report.blockers, *closeout.blockers, *next_decision.blockers]
    if not report.report_passed:
        blockers.append("m060_report_not_passed")
    if not closeout.closeout_succeeded:
        blockers.append("hostname_closeout_not_succeeded")
    if closeout.command != "hostname":
        blockers.append("hostname_closeout_command_not_hostname")
    if next_decision.decision_status != "plan_whoami_identity_command_review":
        blockers.append("m061_decision_not_whoami_review")
    if next_decision.next_allowed_review_command != "whoami":
        blockers.append("m061_next_command_not_whoami")
    status: LambdaM061WhoamiAuthorizationStatus = (
        "authorized_for_future_m061_whoami_identity_command_review"
        if not blockers
        else "not_authorized"
    )
    return LambdaM061WhoamiAuthorization(
        authorization_status=status,
        selected_future_command_set=["whoami"] if status != "not_authorized" else [],
        blockers=sorted(set(blockers)),
        warnings=[
            "M061 authorization is future-only; no whoami command may run now",
            (
                "GPU visibility, Python, package installation, file transfer, "
                "port forwarding, and training remain forbidden"
            ),
        ],
    )


def load_lambda_m061_whoami_authorization(
    path: str | Path,
) -> LambdaM061WhoamiAuthorization:
    return LambdaM061WhoamiAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m061_whoami_authorization(
    path: str | Path,
    report: LambdaM061WhoamiAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
