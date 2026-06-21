"""Build and validate a non-executed future SSH connectivity probe preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_private_key_reference_policy import (
    load_lambda_ssh_private_key_reference_policy,
)

LambdaSSHSafeClientCommandStatus = Literal["safe_preview", "needs_more_design", "blocked"]

REQUIRED_SAFE_OPTIONS = (
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
    "ConnectTimeout=10",
    "ServerAliveInterval=5",
    "ServerAliveCountMax=1",
)

UNSAFE_TOKENS = (
    "-L",
    "-R",
    "-D",
    "-A",
    "-X",
    "-Y",
    "-t",
    "-tt",
    "-W",
    "-w",
    "ProxyCommand",
    "LocalForward",
    "RemoteForward",
    "DynamicForward",
    "scp",
    "sftp",
    "rsync",
)

HOST_PLACEHOLDER = "lambda-user@<redacted-host>"
KEY_REF_PLACEHOLDER = "<redacted-private-key-reference>"


class LambdaSSHSafeClientCommandReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    command_status: LambdaSSHSafeClientCommandStatus
    client_mode: str = "openssh_batch_mode_connectivity_probe"
    command_preview: list[str] = Field(default_factory=list)
    command_preview_redacted: str
    executable: bool = False
    controller_timeout_required: bool = True
    controller_timeout_seconds: int = 15
    handshake_only_guaranteed: bool
    remote_command_present: bool = False
    interactive_shell_requested: bool = False
    file_transfer_detected: bool = False
    port_forwarding_detected: bool = False
    unsafe_ssh_option_detected: bool = False
    private_key_reference_redacted: bool = True
    host_redacted: bool = True
    needs_more_design: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_preview_only(self) -> LambdaSSHSafeClientCommandReport:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.private_key_reference_redacted
            or not self.host_redacted
        ):
            raise ValueError("M054A SSH command preview cannot execute or expose secrets")
        if self.command_status == "safe_preview":
            if (
                self.blockers
                or self.remote_command_present
                or self.interactive_shell_requested
                or self.file_transfer_detected
                or self.port_forwarding_detected
                or self.unsafe_ssh_option_detected
                or not self.handshake_only_guaranteed
            ):
                raise ValueError("safe SSH command preview cannot contain unsafe behavior")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSSHSafeClientCommand = LambdaSSHSafeClientCommandReport


def build_lambda_ssh_safe_client_command_from_path(
    private_key_policy: str | Path,
) -> LambdaSSHSafeClientCommandReport:
    policy = load_lambda_ssh_private_key_reference_policy(private_key_policy)
    blockers = list(policy.blockers)
    if policy.key_reference_policy_status != "policy_defined":
        blockers.append("private_key_reference_policy_not_defined")
    command = build_safe_openssh_connectivity_probe_command()
    validation = validate_ssh_connectivity_command_preview(command)
    blockers.extend(validation["blockers"])
    status: LambdaSSHSafeClientCommandStatus = "safe_preview" if not blockers else "blocked"
    return LambdaSSHSafeClientCommandReport(
        command_status=status,
        command_preview=command,
        command_preview_redacted=" ".join(command),
        handshake_only_guaranteed=not validation["needs_more_design"] and not blockers,
        remote_command_present=validation["remote_command_present"],
        interactive_shell_requested=validation["interactive_shell_requested"],
        file_transfer_detected=validation["file_transfer_detected"],
        port_forwarding_detected=validation["port_forwarding_detected"],
        unsafe_ssh_option_detected=validation["unsafe_ssh_option_detected"],
        needs_more_design=validation["needs_more_design"],
        blockers=sorted(set(blockers)),
        warnings=[
            "M054A does not execute this SSH command preview",
            "SessionType=none and -N are required to avoid shell/session requests",
            "future M054B controller must enforce the local process timeout",
            *policy.warnings,
        ],
    )


def build_safe_openssh_connectivity_probe_command() -> list[str]:
    command = ["ssh"]
    for option in REQUIRED_SAFE_OPTIONS:
        command.extend(["-o", option])
    command.extend(
        [
            "-N",
            "-i",
            KEY_REF_PLACEHOLDER,
            HOST_PLACEHOLDER,
        ]
    )
    return command


def validate_ssh_connectivity_command_preview(command: list[str]) -> dict[str, object]:
    blockers: list[str] = []
    joined = " ".join(command)
    first = command[0] if command else ""
    if first != "ssh":
        blockers.append("ssh_client_required")
    unsafe_found = [token for token in UNSAFE_TOKENS if token in command or token in joined]
    if unsafe_found:
        blockers.extend(f"unsafe_ssh_option:{token}" for token in unsafe_found)
    file_transfer_detected = first in {"scp", "sftp", "rsync"} or any(
        token in {"scp", "sftp", "rsync"} for token in command
    )
    port_forwarding_detected = any(token in command for token in {"-L", "-R", "-D"})
    option_values = _option_values(command)
    missing_options = set(REQUIRED_SAFE_OPTIONS).difference(option_values)
    if missing_options:
        blockers.append(f"missing_required_options:{','.join(sorted(missing_options))}")
    remote_command_present = _remote_command_present(command)
    if remote_command_present:
        blockers.append("remote_command_present")
    interactive_shell_requested = "-N" not in command or "SessionType=none" not in option_values
    if interactive_shell_requested:
        blockers.append("interactive_shell_not_prevented")
    if KEY_REF_PLACEHOLDER not in command:
        blockers.append("redacted_private_key_reference_missing")
    if HOST_PLACEHOLDER not in command:
        blockers.append("redacted_host_placeholder_missing")
    needs_more_design = False
    return {
        "blockers": sorted(set(blockers)),
        "remote_command_present": remote_command_present,
        "interactive_shell_requested": interactive_shell_requested,
        "file_transfer_detected": file_transfer_detected,
        "port_forwarding_detected": port_forwarding_detected,
        "unsafe_ssh_option_detected": bool(unsafe_found),
        "needs_more_design": needs_more_design,
    }


def _option_values(command: list[str]) -> set[str]:
    values: set[str] = set()
    for index, token in enumerate(command[:-1]):
        if token == "-o":
            values.add(command[index + 1])
    return values


def _remote_command_present(command: list[str]) -> bool:
    if HOST_PLACEHOLDER not in command:
        return False
    host_index = command.index(HOST_PLACEHOLDER)
    return len(command) > host_index + 1


def load_lambda_ssh_safe_client_command(
    path: str | Path,
) -> LambdaSSHSafeClientCommandReport:
    return LambdaSSHSafeClientCommandReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_safe_client_command(
    path: str | Path,
    report: LambdaSSHSafeClientCommandReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
