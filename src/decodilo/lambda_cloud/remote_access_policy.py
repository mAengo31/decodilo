"""Remote access policy for future Lambda bootstrap reviews."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaRemoteAccessMode = Literal[
    "no_remote_access",
    "ssh_connectivity_only",
    "ssh_single_allowlisted_command",
    "provider_metadata_only",
]


class LambdaRemoteAccessPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    access_policy_status: Literal["policy_defined", "blocked"]
    default_access_mode: LambdaRemoteAccessMode
    ssh_allowed_without_operator_approval: bool = False
    ssh_key_attachment_implies_ssh_approval: bool = False
    interactive_shell_allowed: bool = False
    arbitrary_shell_allowed: bool = False
    file_transfer_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    background_command_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_access_policy(self) -> LambdaRemoteAccessPolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.ssh_allowed_without_operator_approval
            or self.ssh_key_attachment_implies_ssh_approval
            or self.interactive_shell_allowed
            or self.arbitrary_shell_allowed
            or self.file_transfer_allowed
            or self.package_install_allowed
            or self.training_allowed
            or self.background_command_allowed
        ):
            raise ValueError("remote access policy cannot enable unsafe access")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaRemoteAccessPolicy = LambdaRemoteAccessPolicyReport


def build_lambda_remote_access_policy(
    *,
    default_access_mode: LambdaRemoteAccessMode = "provider_metadata_only",
) -> LambdaRemoteAccessPolicyReport:
    return LambdaRemoteAccessPolicyReport(
        access_policy_status="policy_defined",
        default_access_mode=default_access_mode,
        warnings=[
            "SSH key attachment for launch payload does not approve SSH use",
            "remote access remains disabled unless a future approval artifact allows it",
            "M053 may plan SSH connectivity only, but cannot execute SSH",
        ],
    )


def load_lambda_remote_access_policy(path: str | Path) -> LambdaRemoteAccessPolicyReport:
    return LambdaRemoteAccessPolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_access_policy(
    path: str | Path,
    report: LambdaRemoteAccessPolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
