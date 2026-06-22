"""M055C execution gate-check for SSH diagnostic retry."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_connectivity_m055c_plan import (
    load_lambda_ssh_connectivity_m055c_plan,
)
from decodilo.lambda_cloud.ssh_connectivity_no_exec_audit import (
    load_lambda_ssh_connectivity_no_exec_audit,
)
from decodilo.lambda_cloud.ssh_connectivity_static_validator import (
    load_lambda_ssh_connectivity_static_validation,
)
from decodilo.lambda_cloud.ssh_failure_stderr_capture import (
    load_lambda_ssh_stderr_capture_policy,
)
from decodilo.lambda_cloud.ssh_safe_client_command_builder import (
    load_lambda_ssh_safe_client_command,
    validate_ssh_connectivity_command_preview,
)


class LambdaSSHConnectivityM055CGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M055C"
    gate_passed: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    ssh_username: str = "ubuntu"
    stderr_capture_active: bool = True
    no_remote_command: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_training: bool = True
    max_ssh_attempts: int = 1
    max_launch_attempts: int = 1
    no_auto_retry: bool = True
    command_uses_no_shell_form: bool = True
    safe_command_hash_source: str = "safe_client_command"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHConnectivityM055CGateCheck:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.stderr_capture_active
            or not self.no_remote_command
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_package_install
            or not self.no_training
            or self.max_ssh_attempts != 1
            or self.max_launch_attempts != 1
            or not self.no_auto_retry
        ):
            raise ValueError("M055C gate violates one-shot no-exec constraints")
        if self.gate_passed and self.blockers:
            raise ValueError("passing M055C gate cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_connectivity_m055c_gate_check_from_paths(
    *,
    plan: str | Path,
    safe_client_command: str | Path,
    static_validation: str | Path,
    no_exec_audit: str | Path,
    stderr_capture_policy: str | Path,
) -> LambdaSSHConnectivityM055CGateCheck:
    plan_report = load_lambda_ssh_connectivity_m055c_plan(plan)
    safe = load_lambda_ssh_safe_client_command(safe_client_command)
    static = load_lambda_ssh_connectivity_static_validation(static_validation)
    audit = load_lambda_ssh_connectivity_no_exec_audit(no_exec_audit)
    stderr_policy = load_lambda_ssh_stderr_capture_policy(stderr_capture_policy)
    validation = validate_ssh_connectivity_command_preview(safe.command_preview)

    blockers: list[str] = []
    if plan_report.plan_status != "plan_passed":
        blockers.extend(plan_report.blockers or ["m055c_plan_not_passed"])
    if safe.command_status != "safe_preview":
        blockers.extend(safe.blockers or ["safe_client_command_not_safe"])
    blockers.extend(str(item) for item in validation["blockers"])
    if safe.remote_command_present or validation["remote_command_present"]:
        blockers.append("remote_command_present")
    if safe.interactive_shell_requested or validation["interactive_shell_requested"]:
        blockers.append("interactive_shell_not_prevented")
    if safe.file_transfer_detected or validation["file_transfer_detected"]:
        blockers.append("file_transfer_detected")
    if safe.port_forwarding_detected or validation["port_forwarding_detected"]:
        blockers.append("port_forwarding_detected")
    if safe.unsafe_ssh_option_detected or validation["unsafe_ssh_option_detected"]:
        blockers.append("unsafe_ssh_option_detected")
    if "-N" not in safe.command_preview or "-T" not in safe.command_preview:
        blockers.append("openssh_no_shell_flags_required")
    if not static.static_validation_passed:
        blockers.extend(static.blockers or ["static_validation_not_passed"])
    if not audit.audit_passed:
        blockers.extend(audit.blockers or ["no_exec_audit_not_passed"])
    if stderr_policy.capture_policy_status != "policy_defined":
        blockers.extend(stderr_policy.blockers or ["stderr_capture_policy_not_defined"])
    if not stderr_policy.secret_scan_passed:
        blockers.append("stderr_capture_policy_secret_scan_failed")
    if plan_report.ssh_username != "ubuntu":
        blockers.append("ssh_username_must_be_ubuntu")
    if not plan_report.stderr_capture_enabled:
        blockers.append("stderr_capture_not_enabled")

    return LambdaSSHConnectivityM055CGateCheck(
        gate_passed=not blockers,
        selected_candidate=plan_report.selected_candidate,
        selected_region=plan_report.selected_region,
        ssh_username=plan_report.ssh_username,
        stderr_capture_active=stderr_policy.capture_policy_status == "policy_defined",
        no_remote_command=not safe.remote_command_present,
        no_file_transfer=not safe.file_transfer_detected,
        no_port_forwarding=not safe.port_forwarding_detected,
        no_package_install=not audit.package_install_allowed,
        no_training=not audit.training_allowed,
        max_ssh_attempts=plan_report.max_ssh_attempts,
        max_launch_attempts=plan_report.max_launch_attempts,
        no_auto_retry=plan_report.no_auto_retry,
        command_uses_no_shell_form=(
            "-N" in safe.command_preview and "-T" in safe.command_preview
        ),
        blockers=sorted(set(blockers)),
        warnings=[
            "M055C gate is a pre-launch artifact and does not SSH",
            *plan_report.warnings,
        ],
    )


def load_lambda_ssh_connectivity_m055c_gate_check(
    path: str | Path,
) -> LambdaSSHConnectivityM055CGateCheck:
    return LambdaSSHConnectivityM055CGateCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_m055c_gate_check(
    path: str | Path,
    report: LambdaSSHConnectivityM055CGateCheck,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
