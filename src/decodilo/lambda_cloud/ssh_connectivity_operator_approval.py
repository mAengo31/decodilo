"""Operator approval model for future SSH-connectivity-only M054 review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHConnectivityOperatorApprovalStatus = Literal[
    "not_provided",
    "approved_for_future_m054_ssh_connectivity_review",
    "declined",
]

REQUIRED_SSH_CONNECTIVITY_ACKS = (
    "I approve a future SSH connectivity-only review, not immediate SSH.",
    "I understand SSH connectivity-only means no remote command.",
    "I understand no interactive shell will be opened.",
    "I understand no file transfer will occur.",
    "I understand no port forwarding will occur.",
    "I understand no package install will occur.",
    "I understand no training will occur.",
    "I understand exactly one instance may be launched in a future supervised milestone.",
    "I understand the instance must be terminated and verified.",
    "I understand private key material must not be serialized.",
    "I understand max budget remains $50 and max runtime 30 minutes unless separately changed.",
)


class LambdaSSHConnectivityOperatorApprovalReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    approval_status: LambdaSSHConnectivityOperatorApprovalStatus = "not_provided"
    approval_complete: bool = False
    acknowledgements: list[str] = Field(default_factory=list)
    ssh_authorized_now: bool = False
    launch_authorized_now: bool = False
    remote_exec_allowed: bool = False
    file_transfer_allowed: bool = False
    training_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaSSHConnectivityOperatorApprovalReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.ssh_authorized_now
            or self.launch_authorized_now
            or self.remote_exec_allowed
            or self.file_transfer_allowed
            or self.training_allowed
        ):
            raise ValueError("M053 operator approval cannot authorize immediate SSH or execution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSSHConnectivityOperatorApproval = LambdaSSHConnectivityOperatorApprovalReport


def build_lambda_ssh_connectivity_operator_approval(
    *,
    approve_future_m054: bool = False,
    decline: bool = False,
    acknowledge_all: bool = False,
) -> LambdaSSHConnectivityOperatorApprovalReport:
    blockers: list[str] = []
    if approve_future_m054 and decline:
        blockers.append("multiple_operator_decisions_requested")
    if decline and not blockers:
        return LambdaSSHConnectivityOperatorApprovalReport(
            approval_status="declined",
            approval_complete=True,
            warnings=["operator declined future SSH connectivity review"],
        )
    acknowledgements = list(REQUIRED_SSH_CONNECTIVITY_ACKS) if acknowledge_all else []
    if approve_future_m054:
        missing = sorted(set(REQUIRED_SSH_CONNECTIVITY_ACKS).difference(acknowledgements))
        if missing:
            blockers.append("missing_required_ssh_connectivity_acknowledgements")
        complete = not blockers
        return LambdaSSHConnectivityOperatorApprovalReport(
            approval_status=(
                "approved_for_future_m054_ssh_connectivity_review"
                if complete
                else "not_provided"
            ),
            approval_complete=complete,
            acknowledgements=acknowledgements,
            blockers=blockers,
            warnings=["approval is for future M054 review only and does not execute SSH"],
        )
    return LambdaSSHConnectivityOperatorApprovalReport(
        approval_status="not_provided",
        blockers=blockers,
        warnings=["SSH connectivity operator approval not provided"],
    )


def load_lambda_ssh_connectivity_operator_approval(
    path: str | Path,
) -> LambdaSSHConnectivityOperatorApprovalReport:
    return LambdaSSHConnectivityOperatorApprovalReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_operator_approval(
    path: str | Path,
    report: LambdaSSHConnectivityOperatorApprovalReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
