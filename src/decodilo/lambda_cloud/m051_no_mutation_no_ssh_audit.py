"""Pre-launch M051 audit for no SSH, no commands, and no extra mutation paths."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m050_report import load_lambda_m050_report
from decodilo.lambda_cloud.m051_bootstrap_execution_gate import (
    load_lambda_m051_bootstrap_execution_gate,
)
from decodilo.lambda_cloud.m051_metadata_bootstrap_plan import (
    load_lambda_m051_metadata_bootstrap_plan,
)
from decodilo.lambda_cloud.no_training_policy import load_lambda_no_training_policy
from decodilo.lambda_cloud.package_install_policy import load_lambda_package_install_policy
from decodilo.lambda_cloud.remote_access_policy import load_lambda_remote_access_policy
from decodilo.lambda_cloud.remote_bootstrap_scope import load_lambda_remote_bootstrap_scope
from decodilo.lambda_cloud.remote_command_allowlist import (
    load_lambda_remote_command_allowlist,
)
from decodilo.lambda_cloud.ssh_operator_approval import load_lambda_ssh_operator_approval
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)


class LambdaM051NoMutationNoSSHAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    audit_passed: bool
    restart_paths_allowed: bool = False
    create_delete_resource_paths_allowed: bool = False
    ssh_execution_path_allowed: bool = False
    remote_command_execution_path_allowed: bool = False
    setup_or_cloud_init_path_allowed: bool = False
    package_install_path_allowed: bool = False
    training_path_allowed: bool = False
    raw_ssh_key_name_in_public_reports: bool = False
    metadata_only: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM051NoMutationNoSSHAudit:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.restart_paths_allowed
            or self.create_delete_resource_paths_allowed
            or self.ssh_execution_path_allowed
            or self.remote_command_execution_path_allowed
            or self.setup_or_cloud_init_path_allowed
            or self.package_install_path_allowed
            or self.training_path_allowed
        ):
            raise ValueError("M051 audit cannot pass unsafe paths")
        if self.audit_passed and self.blockers:
            raise ValueError("M051 audit cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_no_mutation_no_ssh_audit_from_paths(
    *,
    metadata_plan: str | Path,
    execution_gate: str | Path,
    scope: str | Path,
    access_policy: str | Path,
    ssh_approval: str | Path,
    command_allowlist: str | Path,
    package_install_policy: str | Path,
    no_training_policy: str | Path,
    m050_report: str | Path,
    ssh_key_selection: str | Path,
    public_artifacts: list[str | Path] | None = None,
) -> LambdaM051NoMutationNoSSHAudit:
    plan = load_lambda_m051_metadata_bootstrap_plan(metadata_plan)
    gate = load_lambda_m051_bootstrap_execution_gate(execution_gate)
    scope_report = load_lambda_remote_bootstrap_scope(scope)
    access = load_lambda_remote_access_policy(access_policy)
    ssh = load_lambda_ssh_operator_approval(ssh_approval)
    commands = load_lambda_remote_command_allowlist(command_allowlist)
    install = load_lambda_package_install_policy(package_install_policy)
    training = load_lambda_no_training_policy(no_training_policy)
    m050 = load_lambda_m050_report(m050_report)
    ssh_selection = load_lambda_existing_ssh_key_selection(ssh_key_selection)

    blockers = [
        *plan.blockers,
        *gate.blockers,
        *scope_report.blockers,
        *access.blockers,
        *ssh.blockers,
        *commands.blockers,
        *install.blockers,
        *training.blockers,
        *m050.blockers,
        *ssh_selection.errors,
    ]
    if not plan.plan_passed:
        blockers.append("metadata_plan_not_passed")
    if not gate.gate_passed:
        blockers.append("execution_gate_not_passed")
    if not m050.report_passed:
        blockers.append("m050_report_not_passed")
    if ssh.approval_status != "declined_no_ssh":
        blockers.append("ssh_not_declined")
    if commands.commands or commands.command_execution_allowed_now:
        blockers.append("remote_command_allowlist_not_empty_or_future_only")
    if install.package_install_allowed:
        blockers.append("package_install_allowed")
    if training.training_allowed:
        blockers.append("training_allowed")
    if scope_report.package_install_allowed or scope_report.training_allowed:
        blockers.append("scope_allows_install_or_training")
    if access.default_access_mode != "provider_metadata_only":
        blockers.append("access_policy_not_provider_metadata_only")
    if access.package_install_allowed or access.training_allowed:
        blockers.append("access_policy_allows_install_or_training")
    if (
        access.interactive_shell_allowed
        or access.arbitrary_shell_allowed
        or access.file_transfer_allowed
        or access.background_command_allowed
        or access.ssh_allowed_without_operator_approval
    ):
        blockers.append("access_policy_allows_ssh_or_remote_commands")
    if plan.ssh_used or gate.ssh_used:
        blockers.append("ssh_used_flag_true")
    if plan.remote_commands_allowed or gate.remote_commands_allowed:
        blockers.append("remote_commands_allowed_flag_true")

    raw_key = ssh_selection.selected_ssh_key_name_for_payload
    leaked = _raw_key_in_public_artifacts(raw_key, public_artifacts or [])
    if leaked:
        blockers.append("raw_ssh_key_name_found_in_public_report")

    return LambdaM051NoMutationNoSSHAudit(
        audit_passed=not blockers,
        raw_ssh_key_name_in_public_reports=leaked,
        blockers=sorted(set(blockers)),
        warnings=[
            "audit permits only read-only discovery plus one launch and owned "
            "termination after arming",
            "raw SSH key name is allowed only in the private SSH selection artifact",
        ],
    )


def _raw_key_in_public_artifacts(
    raw_key: str | None,
    public_artifacts: list[str | Path],
) -> bool:
    if not raw_key:
        return False
    for artifact in public_artifacts:
        path = Path(artifact)
        if not path.exists() or path.is_dir():
            continue
        try:
            if raw_key in path.read_text(encoding="utf-8"):
                return True
        except UnicodeDecodeError:
            continue
    return False


def load_lambda_m051_no_mutation_no_ssh_audit(
    path: str | Path,
) -> LambdaM051NoMutationNoSSHAudit:
    return LambdaM051NoMutationNoSSHAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_no_mutation_no_ssh_audit(
    path: str | Path,
    report: LambdaM051NoMutationNoSSHAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
