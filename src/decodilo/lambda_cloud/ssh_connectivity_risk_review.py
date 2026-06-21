"""Risk review for future SSH-connectivity-only Lambda milestone."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.file_transfer_prohibition_policy import (
    load_lambda_file_transfer_prohibition_policy,
)
from decodilo.lambda_cloud.m052_report import load_lambda_m052_report
from decodilo.lambda_cloud.no_training_policy import load_lambda_no_training_policy
from decodilo.lambda_cloud.package_install_policy import load_lambda_package_install_policy
from decodilo.lambda_cloud.port_forwarding_prohibition_policy import (
    load_lambda_port_forwarding_prohibition_policy,
)
from decodilo.lambda_cloud.remote_command_prohibition_policy import (
    load_lambda_remote_command_prohibition_policy,
)
from decodilo.lambda_cloud.ssh_client_policy import load_lambda_ssh_client_policy
from decodilo.lambda_cloud.ssh_connectivity_evidence_schema import (
    load_lambda_ssh_connectivity_evidence_schema,
)
from decodilo.lambda_cloud.ssh_connectivity_operator_approval import (
    load_lambda_ssh_connectivity_operator_approval,
)
from decodilo.lambda_cloud.ssh_connectivity_scope import load_lambda_ssh_connectivity_scope
from decodilo.lambda_cloud.ssh_credential_policy import load_lambda_ssh_credential_policy

LambdaSSHConnectivityRiskReviewStatus = Literal["passed", "planning_incomplete", "blocked"]


class LambdaSSHConnectivityRiskReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    risk_review_status: LambdaSSHConnectivityRiskReviewStatus
    risk_review_passed: bool
    selected_future_mode: str | None = None
    operator_approval_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaSSHConnectivityRiskReview:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M053 SSH connectivity risk review cannot enable execution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_connectivity_risk_review_from_paths(
    *,
    scope: str | Path,
    credential_policy: str | Path,
    client_policy: str | Path,
    evidence_schema: str | Path,
    operator_approval: str | Path,
    remote_command_prohibition: str | Path,
    file_transfer_prohibition: str | Path,
    port_forwarding_prohibition: str | Path,
    package_install_policy: str | Path,
    no_training_policy: str | Path,
    m052_report: str | Path,
) -> LambdaSSHConnectivityRiskReview:
    scope_report = load_lambda_ssh_connectivity_scope(scope)
    credential = load_lambda_ssh_credential_policy(credential_policy)
    client = load_lambda_ssh_client_policy(client_policy)
    evidence = load_lambda_ssh_connectivity_evidence_schema(evidence_schema)
    approval = load_lambda_ssh_connectivity_operator_approval(operator_approval)
    remote_commands = load_lambda_remote_command_prohibition_policy(remote_command_prohibition)
    file_transfer = load_lambda_file_transfer_prohibition_policy(file_transfer_prohibition)
    forwarding = load_lambda_port_forwarding_prohibition_policy(port_forwarding_prohibition)
    m052 = load_lambda_m052_report(m052_report)
    package_policy = None
    package_policy_blockers: list[str] = []
    package_policy_warnings: list[str] = []
    try:
        package_policy = load_lambda_package_install_policy(package_install_policy)
        package_policy_blockers.extend(package_policy.blockers)
        package_policy_warnings.extend(package_policy.warnings)
    except Exception:  # noqa: BLE001
        package_policy_blockers.append("package_install_policy_invalid")
    training_policy = None
    training_policy_blockers: list[str] = []
    training_policy_warnings: list[str] = []
    try:
        training_policy = load_lambda_no_training_policy(no_training_policy)
        training_policy_blockers.extend(training_policy.blockers)
        training_policy_warnings.extend(training_policy.warnings)
    except Exception:  # noqa: BLE001
        training_policy_blockers.append("training_not_denied")

    blockers = [
        *scope_report.blockers,
        *credential.blockers,
        *client.blockers,
        *evidence.blockers,
        *approval.blockers,
        *remote_commands.blockers,
        *file_transfer.blockers,
        *forwarding.blockers,
        *package_policy_blockers,
        *training_policy_blockers,
        *m052.blockers,
    ]
    if (
        m052.closeout_status not in {"closed_success", "closed_with_warnings"}
        or not m052.report_passed
    ):
        blockers.append("m052_closeout_required")
    if credential.credential_policy_status != "policy_defined":
        blockers.append("ssh_credential_policy_not_defined")
    if evidence.evidence_schema_status != "schema_valid":
        blockers.append("ssh_evidence_schema_not_valid")
    if remote_commands.remote_exec_allowed or remote_commands.interactive_shell_allowed:
        blockers.append("remote_commands_not_prohibited")
    if file_transfer.scp_allowed or file_transfer.sftp_allowed or file_transfer.rsync_allowed:
        blockers.append("file_transfer_not_prohibited")
    if (
        forwarding.local_forward_allowed
        or forwarding.remote_forward_allowed
        or forwarding.dynamic_forward_allowed
    ):
        blockers.append("port_forwarding_not_prohibited")
    if package_policy is not None and package_policy.package_install_allowed:
        blockers.append("package_install_not_denied")
    if training_policy is not None and training_policy.training_allowed:
        blockers.append("training_not_denied")

    approval_ready = (
        approval.approval_status == "approved_for_future_m054_ssh_connectivity_review"
        and approval.approval_complete
    )
    status: LambdaSSHConnectivityRiskReviewStatus
    if blockers:
        status = "blocked"
    elif approval_ready:
        status = "passed"
    else:
        status = "planning_incomplete"
    warnings = [
        "M053 risk review is future-only and does not SSH",
        *scope_report.warnings,
        *credential.warnings,
        *client.warnings,
        *evidence.warnings,
        *approval.warnings,
        *remote_commands.warnings,
        *file_transfer.warnings,
        *forwarding.warnings,
        *package_policy_warnings,
        *training_policy_warnings,
    ]
    if not approval_ready:
        warnings.append("missing operator approval keeps M054 not authorized")

    return LambdaSSHConnectivityRiskReview(
        risk_review_status=status,
        risk_review_passed=status == "passed",
        selected_future_mode=(
            "ssh_connectivity_handshake_only"
            if status in {"passed", "planning_incomplete"}
            else None
        ),
        operator_approval_status=approval.approval_status,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
    )


def load_lambda_ssh_connectivity_risk_review(
    path: str | Path,
) -> LambdaSSHConnectivityRiskReview:
    return LambdaSSHConnectivityRiskReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_risk_review(
    path: str | Path,
    report: LambdaSSHConnectivityRiskReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
