"""Future-only SSH operator approval model for Lambda bootstrap planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHOperatorApprovalStatus = Literal[
    "not_provided",
    "approved_ssh_connectivity_check_only",
    "approved_single_allowlisted_command",
    "declined_no_ssh",
]

SSH_ACKNOWLEDGEMENTS = (
    "I understand an SSH key is attached for launch.",
    "I explicitly approve opening an SSH connection only for connectivity/health verification.",
    "I do not approve interactive shell use.",
    "I do not approve setup scripts.",
    "I do not approve package installation.",
    "I do not approve training.",
    "I do not approve background processes.",
    "I approve only the specific allowlisted command set, if any.",
    "I understand the instance must be terminated and verified.",
)


class LambdaSSHOperatorApprovalReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    approval_status: LambdaSSHOperatorApprovalStatus = "not_provided"
    approval_complete: bool = False
    ssh_connectivity_allowed: bool = False
    single_allowlisted_command_allowed: bool = False
    interactive_shell_allowed: bool = False
    setup_scripts_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    background_process_allowed: bool = False
    acknowledgements: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_ssh_approval(self) -> LambdaSSHOperatorApprovalReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.interactive_shell_allowed
            or self.setup_scripts_allowed
            or self.package_install_allowed
            or self.training_allowed
            or self.background_process_allowed
        ):
            raise ValueError("SSH approval cannot enable unsafe or immediate execution")
        if self.single_allowlisted_command_allowed and not self.ssh_connectivity_allowed:
            raise ValueError("single command approval requires SSH connectivity approval")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSSHOperatorApproval = LambdaSSHOperatorApprovalReport


def build_lambda_ssh_operator_approval(
    *,
    decline_ssh: bool = False,
    approve_connectivity_only: bool = False,
    approve_single_allowlisted_command: bool = False,
    acknowledge_all: bool = False,
) -> LambdaSSHOperatorApprovalReport:
    requested = [
        decline_ssh,
        approve_connectivity_only,
        approve_single_allowlisted_command,
    ]
    blockers: list[str] = []
    if sum(1 for item in requested if item) > 1:
        blockers.append("multiple_ssh_approval_modes_requested")
    acknowledgements = list(SSH_ACKNOWLEDGEMENTS) if acknowledge_all else []
    if decline_ssh and not blockers:
        return LambdaSSHOperatorApprovalReport(
            approval_status="declined_no_ssh",
            approval_complete=True,
            warnings=["SSH declined for M050 default metadata-only planning"],
        )
    if approve_connectivity_only or approve_single_allowlisted_command:
        if not acknowledge_all:
            blockers.append("missing_required_ssh_acknowledgements")
        complete = not blockers
        return LambdaSSHOperatorApprovalReport(
            approval_status=(
                "approved_single_allowlisted_command"
                if approve_single_allowlisted_command and complete
                else (
                    "approved_ssh_connectivity_check_only"
                    if approve_connectivity_only and complete
                    else "not_provided"
                )
            ),
            approval_complete=complete,
            ssh_connectivity_allowed=complete,
            single_allowlisted_command_allowed=(
                approve_single_allowlisted_command and complete
            ),
            acknowledgements=acknowledgements,
            blockers=blockers,
            warnings=[
                "SSH approval is future-review only and does not execute SSH",
                "M053 uses a separate SSH-connectivity-only approval model for M054",
            ],
        )
    return LambdaSSHOperatorApprovalReport(
        approval_status="not_provided",
        blockers=blockers,
        warnings=[
            "SSH approval not provided",
            "M053 uses a separate SSH-connectivity-only approval model for M054",
        ],
    )


def load_lambda_ssh_operator_approval(path: str | Path) -> LambdaSSHOperatorApprovalReport:
    return LambdaSSHOperatorApprovalReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_operator_approval(
    path: str | Path,
    report: LambdaSSHOperatorApprovalReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
