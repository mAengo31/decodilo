"""Future-only M059 identity command authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_command_stage_policy import (
    load_lambda_remote_command_stage_policy,
)
from decodilo.lambda_cloud.smallest_useful_command_review import (
    load_lambda_smallest_useful_command_review,
)
from decodilo.lambda_cloud.ssh_noop_command_closeout import (
    load_lambda_ssh_noop_command_closeout,
)

M059AuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m059_identity_command_review",
]


class LambdaM059RemoteCommandAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: M059AuthorizationStatus
    selected_future_command_set: list[str] = Field(default_factory=list)
    future_review_only: bool = True
    launch_authorized_now: bool = False
    command_authorized_now: bool = False
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
    def _validate_future_only(self) -> LambdaM059RemoteCommandAuthorization:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.launch_authorized_now
            or self.command_authorized_now
            or self.package_install_allowed
            or self.training_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
        ):
            raise ValueError("M059 authorization cannot authorize immediate execution")
        if self.authorization_status == "authorized_for_future_m059_identity_command_review":
            if self.blockers or self.selected_future_command_set not in (
                ["hostname"],
                ["hostname", "whoami"],
            ):
                raise ValueError("M059 authorization requires only identity commands")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m059_remote_command_authorization_from_paths(
    *,
    ssh_noop_closeout: str | Path,
    stage_policy: str | Path,
    command_review: str | Path,
) -> LambdaM059RemoteCommandAuthorization:
    closeout = load_lambda_ssh_noop_command_closeout(ssh_noop_closeout)
    policy = load_lambda_remote_command_stage_policy(stage_policy)
    review = load_lambda_smallest_useful_command_review(command_review)
    blockers = [*closeout.blockers, *policy.blockers, *review.blockers]
    if not closeout.closeout_succeeded:
        blockers.append("ssh_noop_closeout_not_succeeded")
    if policy.policy_status != "policy_defined":
        blockers.append("stage_policy_not_defined")
    if policy.current_accepted_stage != "noop_command_only":
        blockers.append("noop_stage_not_established")
    if review.review_status != "review_passed":
        blockers.append("smallest_command_review_not_passed")
    if review.recommended_next_command_stage != "identity_command":
        blockers.append("next_stage_not_identity_command")
    if review.selected_future_command_set not in (["hostname"], ["hostname", "whoami"]):
        blockers.append("selected_command_set_not_identity_only")
    status: M059AuthorizationStatus = (
        "authorized_for_future_m059_identity_command_review"
        if not blockers
        else "not_authorized"
    )
    return LambdaM059RemoteCommandAuthorization(
        authorization_status=status,
        selected_future_command_set=(
            review.selected_future_command_set if status != "not_authorized" else []
        ),
        blockers=sorted(set(blockers)),
        warnings=[
            "M059 authorization is future-only; no command may run from M058",
            "package install, file transfer, port forwarding, and training remain forbidden",
        ],
    )


def load_lambda_m059_remote_command_authorization(
    path: str | Path,
) -> LambdaM059RemoteCommandAuthorization:
    return LambdaM059RemoteCommandAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m059_remote_command_authorization(
    path: str | Path,
    report: LambdaM059RemoteCommandAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
