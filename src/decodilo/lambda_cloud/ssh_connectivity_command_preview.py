"""Non-executable command preview for future M054B SSH connectivity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_connectivity_no_exec_audit import (
    load_lambda_ssh_connectivity_no_exec_audit,
)
from decodilo.lambda_cloud.ssh_connectivity_reviewer_bridge import (
    load_lambda_ssh_connectivity_reviewer_bridge,
)

LambdaSSHConnectivityCommandPreviewStatus = Literal[
    "ready_for_future_m054b_ssh_connectivity_review",
    "blocked",
]


class LambdaSSHConnectivityCommandPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: LambdaSSHConnectivityCommandPreviewStatus
    executable: bool = False
    future_workdir_placeholder: str = "/tmp/decodilo-lambda-m054b"
    command_preview: list[str] = Field(default_factory=list)
    lifecycle_steps: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    raw_ssh_key_present: bool = False
    secret_like_value_present: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_preview(self) -> LambdaSSHConnectivityCommandPreview:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.raw_ssh_key_present
            or self.secret_like_value_present
        ):
            raise ValueError("M054 SSH command preview must remain non-executable")
        if self.preview_status != "blocked" and self.blockers:
            raise ValueError("ready M054 command preview cannot have blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_connectivity_command_preview_from_paths(
    *,
    reviewer_bridge: str | Path,
    no_exec_audit: str | Path,
) -> LambdaSSHConnectivityCommandPreview:
    bridge = load_lambda_ssh_connectivity_reviewer_bridge(reviewer_bridge)
    audit = load_lambda_ssh_connectivity_no_exec_audit(no_exec_audit)
    blockers = [*bridge.blockers, *audit.blockers]
    if bridge.bridge_status != "reviewer_compatible_one_shot_ready":
        blockers.append("reviewer_bridge_not_ready")
    if not audit.audit_passed:
        blockers.append("no_exec_audit_failed")
    return LambdaSSHConnectivityCommandPreview(
        preview_status=(
            "ready_for_future_m054b_ssh_connectivity_review"
            if not blockers
            else "blocked"
        ),
        command_preview=_command_preview() if not blockers else [],
        lifecycle_steps=[
            "fresh read-only Lambda discovery before launch",
            "supervised one-instance launch if separately armed",
            "provider/API metadata collection",
            "bounded SSH connectivity/authentication probe only",
            "owned-instance termination",
            "read-only termination verification",
        ],
        forbidden_actions=[
            "interactive shell",
            "remote command",
            "file transfer",
            "port forwarding",
            "package install",
            "setup script",
            "cloud-init",
            "training",
        ],
        blockers=sorted(set(blockers)),
        warnings=[
            "M054A does not execute this preview",
            "future M054B remains separately supervised and billable",
            *bridge.warnings,
            *audit.warnings,
        ],
    )


def _command_preview() -> list[str]:
    return [
        "python",
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--workdir",
        "/tmp/decodilo-lambda-m054b",
        "--m054b-plan",
        "/tmp/decodilo-lambda-m054b-plan.json",
        "--m054-ssh-one-shot-arming",
        "/tmp/decodilo-lambda-m054-ssh-one-shot-arming.json",
        "--m054-ssh-reviewer-bridge",
        "/tmp/decodilo-lambda-m054-ssh-reviewer-bridge.json",
        "--m054-ssh-static-validation",
        "/tmp/decodilo-lambda-ssh-connectivity-static-validation.json",
        "--m054-ssh-no-exec-audit",
        "/tmp/decodilo-lambda-ssh-connectivity-no-exec-audit.json",
        "--m054-ssh-command-preview",
        "/tmp/decodilo-lambda-m054-ssh-command-preview.json",
        "--m054-ssh-safe-client-command",
        "/tmp/decodilo-lambda-ssh-safe-client-command.json",
        "--ssh-key-selection",
        "/tmp/decodilo-lambda-strand-ssh-key-selection.json",
        "--response-loss-controls",
        "/tmp/decodilo-lambda-strand-response-loss-controls.json",
        "--execute-real-launch",
        "--confirm-billable-action",
        "<operator-confirmation-required>",
        "--confirm-terminate-required",
        "<operator-confirmation-required>",
    ]


def load_lambda_ssh_connectivity_command_preview(
    path: str | Path,
) -> LambdaSSHConnectivityCommandPreview:
    return LambdaSSHConnectivityCommandPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_command_preview(
    path: str | Path,
    report: LambdaSSHConnectivityCommandPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
