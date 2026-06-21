"""Static validation for future SSH-connectivity-only execution artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_connectivity_execution_plan import (
    load_lambda_ssh_connectivity_execution_plan,
)
from decodilo.lambda_cloud.ssh_private_key_reference_policy import (
    load_lambda_ssh_private_key_reference_policy,
)
from decodilo.lambda_cloud.ssh_safe_client_command_builder import (
    load_lambda_ssh_safe_client_command,
    validate_ssh_connectivity_command_preview,
)


class LambdaSSHConnectivityStaticValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    static_validation_passed: bool
    remote_exec_detected: bool = False
    file_transfer_detected: bool = False
    port_forwarding_detected: bool = False
    package_install_detected: bool = False
    training_detected: bool = False
    unsafe_ssh_option_detected: bool = False
    needs_more_design: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_static_report(self) -> LambdaSSHConnectivityStaticValidationReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M054A static validation cannot enable execution")
        if self.static_validation_passed and (
            self.blockers
            or self.remote_exec_detected
            or self.file_transfer_detected
            or self.port_forwarding_detected
            or self.package_install_detected
            or self.training_detected
            or self.unsafe_ssh_option_detected
            or self.needs_more_design
        ):
            raise ValueError("passing static validation cannot carry unsafe detections")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSSHConnectivityStaticValidator = LambdaSSHConnectivityStaticValidationReport


def build_lambda_ssh_connectivity_static_validation_from_paths(
    *,
    execution_plan: str | Path,
    private_key_policy: str | Path,
    safe_client_command: str | Path,
) -> LambdaSSHConnectivityStaticValidationReport:
    plan = load_lambda_ssh_connectivity_execution_plan(execution_plan)
    key_policy = load_lambda_ssh_private_key_reference_policy(private_key_policy)
    command = load_lambda_ssh_safe_client_command(safe_client_command)
    command_validation = validate_ssh_connectivity_command_preview(command.command_preview)
    blockers = [
        *plan.blockers,
        *key_policy.blockers,
        *command.blockers,
        *command_validation["blockers"],
    ]
    if plan.plan_status != "plan_defined":
        blockers.append("execution_plan_not_defined")
    if key_policy.key_reference_policy_status != "policy_defined":
        blockers.append("private_key_reference_policy_not_defined")
    if command.command_status != "safe_preview":
        blockers.append("safe_client_command_not_safe")
    remote_exec = bool(command.remote_command_present)
    file_transfer = bool(command.file_transfer_detected)
    port_forwarding = bool(command.port_forwarding_detected)
    unsafe_option = bool(command.unsafe_ssh_option_detected)
    package_install = bool(plan.package_install_allowed)
    training = bool(plan.training_allowed)
    needs_more_design = bool(command.needs_more_design)
    if remote_exec:
        blockers.append("remote_exec_detected")
    if file_transfer:
        blockers.append("file_transfer_detected")
    if port_forwarding:
        blockers.append("port_forwarding_detected")
    if unsafe_option:
        blockers.append("unsafe_ssh_option_detected")
    if package_install:
        blockers.append("package_install_detected")
    if training:
        blockers.append("training_detected")
    if needs_more_design:
        blockers.append("ssh_probe_needs_more_design")

    return LambdaSSHConnectivityStaticValidationReport(
        static_validation_passed=not blockers,
        remote_exec_detected=remote_exec,
        file_transfer_detected=file_transfer,
        port_forwarding_detected=port_forwarding,
        package_install_detected=package_install,
        training_detected=training,
        unsafe_ssh_option_detected=unsafe_option,
        needs_more_design=needs_more_design,
        blockers=sorted(set(str(blocker) for blocker in blockers)),
        warnings=[
            "M054A static validation is offline and does not SSH",
            *plan.warnings,
            *key_policy.warnings,
            *command.warnings,
        ],
    )


def load_lambda_ssh_connectivity_static_validation(
    path: str | Path,
) -> LambdaSSHConnectivityStaticValidationReport:
    return LambdaSSHConnectivityStaticValidationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_static_validation(
    path: str | Path,
    report: LambdaSSHConnectivityStaticValidationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
