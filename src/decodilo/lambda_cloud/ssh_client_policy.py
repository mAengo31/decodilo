"""SSH client policy for future connectivity-only Lambda review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHClient = Literal["none", "openssh_batch_mode", "python_ssh_library"]
LambdaSSHClientPolicyStatus = Literal["policy_defined", "blocked"]

SAFE_OPENSSH_OPTIONS = {
    "BatchMode=yes",
    "RequestTTY=no",
    "ClearAllForwardings=yes",
    "ForwardAgent=no",
    "ForwardX11=no",
    "PermitLocalCommand=no",
    "ControlMaster=no",
    "SessionType=none",
    "PasswordAuthentication=no",
    "NumberOfPasswordPrompts=0",
}

UNSAFE_OPTION_TOKENS = ("-tt", "-t", "-A", "-X", "-Y", "-L", "-R", "-D", "-Nf", "ProxyCommand")


class LambdaSSHClientPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    client_policy_status: LambdaSSHClientPolicyStatus = "policy_defined"
    allowed_client: LambdaSSHClient = "none"
    future_allowed_client_options: list[str] = Field(
        default_factory=lambda: [
            "openssh_batch_mode",
            "openssh_batch_mode_connectivity_probe",
        ]
    )
    required_openssh_safety_options: list[str] = Field(
        default_factory=lambda: sorted(SAFE_OPENSSH_OPTIONS)
    )
    remote_command_allowed: bool = False
    tty_allowed: bool = False
    port_forwarding_allowed: bool = False
    agent_forwarding_allowed: bool = False
    x11_forwarding_allowed: bool = False
    file_transfer_allowed: bool = False
    controlmaster_reuse_allowed: bool = False
    backgrounding_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_client_policy(self) -> LambdaSSHClientPolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.allowed_client != "none"
            or self.remote_command_allowed
            or self.tty_allowed
            or self.port_forwarding_allowed
            or self.agent_forwarding_allowed
            or self.x11_forwarding_allowed
            or self.file_transfer_allowed
            or self.controlmaster_reuse_allowed
            or self.backgrounding_allowed
        ):
            raise ValueError(
                "M053 SSH client policy cannot execute or enable unsafe SSH features"
            )
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSSHClientPolicy = LambdaSSHClientPolicyReport


def validate_future_openssh_options(
    options: list[str],
    *,
    remote_command: str | None = None,
) -> list[str]:
    blockers: list[str] = []
    if remote_command:
        blockers.append("remote_command_present")
    joined = " ".join(options)
    for token in UNSAFE_OPTION_TOKENS:
        if token in joined:
            blockers.append(f"unsafe_ssh_option:{token}")
    missing = SAFE_OPENSSH_OPTIONS.difference(options)
    if missing:
        blockers.append(f"missing_required_ssh_options:{','.join(sorted(missing))}")
    return sorted(set(blockers))


def build_lambda_ssh_client_policy() -> LambdaSSHClientPolicyReport:
    return LambdaSSHClientPolicyReport(
        warnings=[
            "M053 default SSH client is none; no SSH client may execute",
            "future M054 may review OpenSSH batch mode connectivity probe only "
            "with explicit approval",
            "M054A requires SessionType=none and no remote command for OpenSSH previews",
        ],
    )


def load_lambda_ssh_client_policy(path: str | Path) -> LambdaSSHClientPolicyReport:
    return LambdaSSHClientPolicyReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_ssh_client_policy(path: str | Path, report: LambdaSSHClientPolicyReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
