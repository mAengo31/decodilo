"""No-execution audit for future SSH-connectivity-only milestone."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_connectivity_execution_plan import (
    load_lambda_ssh_connectivity_execution_plan,
)
from decodilo.lambda_cloud.ssh_safe_client_command_builder import (
    load_lambda_ssh_safe_client_command,
)


class LambdaSSHConnectivityNoExecAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    remote_exec_allowed: bool = False
    interactive_shell_allowed: bool = False
    command_string_present: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    audit_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_audit(self) -> LambdaSSHConnectivityNoExecAudit:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M054A no-exec audit cannot enable execution")
        if self.audit_passed and (
            self.blockers
            or self.remote_exec_allowed
            or self.interactive_shell_allowed
            or self.command_string_present
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or self.package_install_allowed
            or self.training_allowed
        ):
            raise ValueError("passing no-exec audit cannot contain execution surfaces")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_connectivity_no_exec_audit_from_paths(
    *,
    execution_plan: str | Path,
    safe_client_command: str | Path,
) -> LambdaSSHConnectivityNoExecAudit:
    plan = load_lambda_ssh_connectivity_execution_plan(execution_plan)
    command = load_lambda_ssh_safe_client_command(safe_client_command)
    remote_exec = bool(plan.remote_exec_allowed or command.remote_command_present)
    interactive_shell = bool(
        plan.interactive_shell_allowed or command.interactive_shell_requested
    )
    file_transfer = bool(plan.file_transfer_allowed or command.file_transfer_detected)
    forwarding = bool(plan.port_forwarding_allowed or command.port_forwarding_detected)
    package_install = bool(plan.package_install_allowed)
    training = bool(plan.training_allowed)
    command_string_present = bool(command.remote_command_present)
    blockers = [*plan.blockers, *command.blockers]
    if remote_exec:
        blockers.append("remote_exec_allowed")
    if interactive_shell:
        blockers.append("interactive_shell_allowed")
    if command_string_present:
        blockers.append("command_string_present")
    if file_transfer:
        blockers.append("file_transfer_allowed")
    if forwarding:
        blockers.append("port_forwarding_allowed")
    if package_install:
        blockers.append("package_install_allowed")
    if training:
        blockers.append("training_allowed")
    return LambdaSSHConnectivityNoExecAudit(
        remote_exec_allowed=remote_exec,
        interactive_shell_allowed=interactive_shell,
        command_string_present=command_string_present,
        file_transfer_allowed=file_transfer,
        port_forwarding_allowed=forwarding,
        package_install_allowed=package_install,
        training_allowed=training,
        audit_passed=not blockers,
        blockers=sorted(set(blockers)),
        warnings=[
            "M054A no-exec audit is offline and does not SSH",
            *plan.warnings,
            *command.warnings,
        ],
    )


def load_lambda_ssh_connectivity_no_exec_audit(
    path: str | Path,
) -> LambdaSSHConnectivityNoExecAudit:
    return LambdaSSHConnectivityNoExecAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_no_exec_audit(
    path: str | Path,
    report: LambdaSSHConnectivityNoExecAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
