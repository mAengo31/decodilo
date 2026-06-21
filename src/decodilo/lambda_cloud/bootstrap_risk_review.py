"""Risk review for future Lambda remote bootstrap planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bootstrap_evidence_schema import (
    load_lambda_bootstrap_evidence_schema,
)
from decodilo.lambda_cloud.lifecycle_smoke_closeout import (
    load_lambda_lifecycle_smoke_closeout,
)
from decodilo.lambda_cloud.no_training_policy import load_lambda_no_training_policy
from decodilo.lambda_cloud.package_install_policy import (
    load_lambda_package_install_policy,
)
from decodilo.lambda_cloud.remote_access_policy import load_lambda_remote_access_policy
from decodilo.lambda_cloud.remote_bootstrap_scope import load_lambda_remote_bootstrap_scope
from decodilo.lambda_cloud.remote_command_allowlist import (
    load_lambda_remote_command_allowlist,
)
from decodilo.lambda_cloud.ssh_operator_approval import load_lambda_ssh_operator_approval

LambdaBootstrapMode = Literal[
    "lifecycle_plus_metadata_only",
    "lifecycle_plus_ssh_connectivity_check",
    "lifecycle_plus_single_benign_command",
]


class LambdaBootstrapRiskReviewReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    risk_review_passed: bool
    selected_bootstrap_mode: LambdaBootstrapMode | None = None
    lifecycle_closeout_status: str | None = None
    lifecycle_closeout_succeeded: bool = False
    ssh_approval_status: str
    command_allowlist_status: str
    package_install_policy_status: str
    no_training_policy_status: str
    evidence_schema_status: str
    risks: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaBootstrapRiskReviewReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("bootstrap risk review cannot enable launch")
        if self.risk_review_passed and self.blockers:
            raise ValueError("risk review cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_bootstrap_risk_review_from_paths(
    *,
    scope: str | Path,
    access_policy: str | Path,
    ssh_approval: str | Path,
    command_allowlist: str | Path,
    package_install_policy: str | Path,
    no_training_policy: str | Path,
    evidence_schema: str | Path,
    lifecycle_closeout: str | Path | None = None,
) -> LambdaBootstrapRiskReviewReport:
    scope_report = load_lambda_remote_bootstrap_scope(scope)
    access = load_lambda_remote_access_policy(access_policy)
    ssh = load_lambda_ssh_operator_approval(ssh_approval)
    commands = load_lambda_remote_command_allowlist(command_allowlist)
    install = load_lambda_package_install_policy(package_install_policy)
    no_training = load_lambda_no_training_policy(no_training_policy)
    evidence = load_lambda_bootstrap_evidence_schema(evidence_schema)
    closeout = (
        None
        if lifecycle_closeout is None or not Path(lifecycle_closeout).exists()
        else load_lambda_lifecycle_smoke_closeout(lifecycle_closeout)
    )

    blockers = [
        *scope_report.blockers,
        *access.blockers,
        *ssh.blockers,
        *commands.blockers,
        *install.blockers,
        *no_training.blockers,
        *evidence.blockers,
    ]
    risks = [
        "future M051 launch remains billable if later approved",
        "remote bootstrap must terminate the owned instance in the same supervised run",
    ]
    if closeout is None:
        blockers.append("lifecycle_smoke_closeout_not_verified")
    elif not closeout.closeout_succeeded:
        blockers.append("lifecycle_smoke_closeout_not_succeeded")

    selected_mode = scope_report.default_experiment_type
    if selected_mode == "lifecycle_plus_metadata_only":
        if ssh.approval_status not in {"declined_no_ssh", "not_provided"}:
            blockers.append("metadata_only_mode_must_not_require_ssh")
        if commands.commands:
            blockers.append("metadata_only_mode_requires_empty_command_allowlist")
    elif selected_mode == "lifecycle_plus_ssh_connectivity_check":
        if ssh.approval_status != "approved_ssh_connectivity_check_only":
            blockers.append("ssh_connectivity_mode_requires_ssh_approval")
    elif selected_mode == "lifecycle_plus_single_benign_command":
        if ssh.approval_status != "approved_single_allowlisted_command":
            blockers.append("command_mode_requires_single_command_ssh_approval")
        if not commands.commands:
            blockers.append("command_mode_requires_non_empty_allowlist")

    if install.package_install_allowed:
        blockers.append("package_install_policy_must_deny_installs")
    if no_training.training_allowed:
        blockers.append("no_training_policy_must_deny_training")
    if not evidence.schema_valid:
        blockers.append("bootstrap_evidence_schema_not_valid")
    if access.default_access_mode in {
        "ssh_connectivity_only",
        "ssh_single_allowlisted_command",
    } and ssh.approval_status in {"declined_no_ssh", "not_provided"}:
        blockers.append("access_policy_requires_ssh_without_approval")

    return LambdaBootstrapRiskReviewReport(
        risk_review_passed=not blockers,
        selected_bootstrap_mode=None if blockers else selected_mode,
        lifecycle_closeout_status=None if closeout is None else closeout.closeout_status,
        lifecycle_closeout_succeeded=False
        if closeout is None
        else closeout.closeout_succeeded,
        ssh_approval_status=ssh.approval_status,
        command_allowlist_status=commands.command_allowlist_status,
        package_install_policy_status=install.package_install_policy_status,
        no_training_policy_status=no_training.no_training_policy_status,
        evidence_schema_status=evidence.evidence_schema_status,
        risks=risks,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M050 risk review is future-only and does not launch",
                    *scope_report.warnings,
                    *access.warnings,
                    *ssh.warnings,
                    *commands.warnings,
                    *install.warnings,
                    *no_training.warnings,
                    *evidence.warnings,
                    *(closeout.warnings if closeout is not None else []),
                ]
            )
        ),
    )


def load_lambda_bootstrap_risk_review(path: str | Path) -> LambdaBootstrapRiskReviewReport:
    return LambdaBootstrapRiskReviewReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_bootstrap_risk_review(
    path: str | Path,
    report: LambdaBootstrapRiskReviewReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
