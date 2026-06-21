"""Bounded SSH connectivity/authentication probe for M054B."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.real_launch_result import redact_instance_id
from decodilo.lambda_cloud.ssh_host_discovery import (
    LambdaSSHHostDiscoveryResult,
    extract_ssh_host_from_instance_metadata,
)
from decodilo.lambda_cloud.ssh_safe_client_command_builder import (
    load_lambda_ssh_safe_client_command,
    validate_ssh_connectivity_command_preview,
)

LambdaSSHConnectivityAuthResult = Literal[
    "not_attempted",
    "fake_probe_succeeded",
    "auth_succeeded",
    "auth_succeeded_timeout_after_probe_window",
    "auth_failed",
    "connection_failed",
    "blocked",
    "ssh_key_missing",
    "host_discovery_failed",
]


class LambdaSSHConnectivityProbeEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    probe_attempted: bool = False
    probe_completed: bool = False
    probe_passed: bool = False
    auth_result: LambdaSSHConnectivityAuthResult = "not_attempted"
    owned_instance_id_redacted: str | None = None
    target_host_redacted: str = "<redacted-host>"
    host_discovery_attempted: bool = False
    host_discovery_status: str | None = None
    host_discovery_source_path: str | None = None
    host_discovery_poll_count: int = 0
    host_discovery_duration_seconds: float = 0.0
    sanitized_metadata_keys: list[str] = Field(default_factory=list)
    sanitized_metadata_key_paths: list[str] = Field(default_factory=list)
    ssh_key_present: bool = False
    ssh_key_permissions_too_open: bool = False
    private_key_reference_redacted: str = "<redacted-private-key-reference>"
    ssh_username: str = "ubuntu"
    client_mode: str = "openssh_batch_mode_connectivity_probe"
    bounded_timeout_seconds: int = 15
    exit_status: int | None = None
    elapsed_seconds: float = 0.0
    remote_command_attempted: bool = False
    interactive_shell_attempted: bool = False
    file_transfer_attempted: bool = False
    port_forwarding_attempted: bool = False
    package_install_attempted: bool = False
    training_attempted: bool = False
    command_output_collected: bool = False
    stdout_stored: bool = False
    stderr_stored: bool = False
    retry_attempted: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_no_exec(self) -> LambdaSSHConnectivityProbeEvidence:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.remote_command_attempted
            or self.interactive_shell_attempted
            or self.file_transfer_attempted
            or self.port_forwarding_attempted
            or self.package_install_attempted
            or self.training_attempted
            or self.command_output_collected
            or self.stdout_stored
            or self.stderr_stored
            or self.retry_attempted
        ):
            raise ValueError("M054B SSH probe evidence violates no-exec constraints")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_connectivity_probe_not_attempted(
    *,
    owned_instance_id: str | None = None,
    reason: str,
) -> LambdaSSHConnectivityProbeEvidence:
    return LambdaSSHConnectivityProbeEvidence(
        owned_instance_id_redacted=redact_instance_id(owned_instance_id),
        auth_result="blocked",
        blockers=[reason],
        warnings=["SSH connectivity probe was not attempted"],
    )


def run_lambda_ssh_connectivity_probe(
    *,
    owned_instance_id: str,
    instance_payload: dict[str, Any],
    private_key_path: Path | None,
    safe_client_command: str | Path,
    ssh_username: str = "ubuntu",
    timeout_seconds: int = 15,
    fake_mode: bool = False,
    host_discovery_result: LambdaSSHHostDiscoveryResult | None = None,
) -> LambdaSSHConnectivityProbeEvidence:
    safe = load_lambda_ssh_safe_client_command(safe_client_command)
    validation = validate_ssh_connectivity_command_preview(safe.command_preview)
    blockers = [*safe.blockers, *[str(item) for item in validation["blockers"]]]
    if safe.command_status != "safe_preview":
        blockers.append("safe_client_command_not_safe")
    if blockers:
        return LambdaSSHConnectivityProbeEvidence(
            owned_instance_id_redacted=redact_instance_id(owned_instance_id),
            auth_result="blocked",
            blockers=sorted(set(blockers)),
        )
    if host_discovery_result is None:
        host_discovery_result = extract_ssh_host_from_instance_metadata(instance_payload)
    if host_discovery_result.status != "FOUND" or not host_discovery_result.host:
        return LambdaSSHConnectivityProbeEvidence(
            owned_instance_id_redacted=redact_instance_id(owned_instance_id),
            auth_result="host_discovery_failed",
            host_discovery_attempted=True,
            host_discovery_status=host_discovery_result.status,
            host_discovery_source_path=host_discovery_result.source_path,
            host_discovery_poll_count=host_discovery_result.poll_count,
            host_discovery_duration_seconds=host_discovery_result.duration_seconds,
            sanitized_metadata_keys=host_discovery_result.sanitized_metadata_keys,
            sanitized_metadata_key_paths=host_discovery_result.sanitized_metadata_key_paths,
            blockers=["ssh_host_not_present_in_provider_metadata"],
        )
    if fake_mode:
        return LambdaSSHConnectivityProbeEvidence(
            probe_attempted=True,
            probe_completed=True,
            probe_passed=True,
            auth_result="fake_probe_succeeded",
            owned_instance_id_redacted=redact_instance_id(owned_instance_id),
            target_host_redacted=host_discovery_result.host_redacted or "<redacted-host>",
            host_discovery_attempted=True,
            host_discovery_status=host_discovery_result.status,
            host_discovery_source_path=host_discovery_result.source_path,
            host_discovery_poll_count=host_discovery_result.poll_count,
            host_discovery_duration_seconds=host_discovery_result.duration_seconds,
            sanitized_metadata_keys=host_discovery_result.sanitized_metadata_keys,
            sanitized_metadata_key_paths=host_discovery_result.sanitized_metadata_key_paths,
            ssh_key_present=private_key_path is not None,
            ssh_username=ssh_username,
            elapsed_seconds=0.0,
            warnings=["fake-server mode did not open an SSH socket"],
        )
    if private_key_path is None or not private_key_path.is_file():
        return LambdaSSHConnectivityProbeEvidence(
            owned_instance_id_redacted=redact_instance_id(owned_instance_id),
            auth_result="ssh_key_missing",
            host_discovery_attempted=True,
            host_discovery_status=host_discovery_result.status,
            host_discovery_source_path=host_discovery_result.source_path,
            host_discovery_poll_count=host_discovery_result.poll_count,
            host_discovery_duration_seconds=host_discovery_result.duration_seconds,
            sanitized_metadata_keys=host_discovery_result.sanitized_metadata_keys,
            sanitized_metadata_key_paths=host_discovery_result.sanitized_metadata_key_paths,
            ssh_key_present=False,
            blockers=["ssh_key_missing"],
        )

    command = _real_ssh_command(
        host=host_discovery_result.host,
        private_key_path=private_key_path,
        ssh_username=ssh_username,
    )
    started = time.monotonic()
    try:
        completed = subprocess.run(  # noqa: S603 - command is statically validated.
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return LambdaSSHConnectivityProbeEvidence(
            probe_attempted=True,
            probe_completed=False,
            probe_passed=True,
            auth_result="auth_succeeded_timeout_after_probe_window",
            owned_instance_id_redacted=redact_instance_id(owned_instance_id),
            target_host_redacted=host_discovery_result.host_redacted or "<redacted-host>",
            host_discovery_attempted=True,
            host_discovery_status=host_discovery_result.status,
            host_discovery_source_path=host_discovery_result.source_path,
            host_discovery_poll_count=host_discovery_result.poll_count,
            host_discovery_duration_seconds=host_discovery_result.duration_seconds,
            sanitized_metadata_keys=host_discovery_result.sanitized_metadata_keys,
            sanitized_metadata_key_paths=host_discovery_result.sanitized_metadata_key_paths,
            ssh_key_present=True,
            ssh_key_permissions_too_open=bool(private_key_path.stat().st_mode & 0o077),
            ssh_username=ssh_username,
            elapsed_seconds=round(time.monotonic() - started, 6),
            warnings=[
                "OpenSSH -N/-T held the connection until the bounded local timeout; "
                "no remote command output was collected"
            ],
        )
    elapsed = round(time.monotonic() - started, 6)
    if completed.returncode == 0:
        auth_result: LambdaSSHConnectivityAuthResult = "auth_succeeded"
        passed = True
        errors: list[str] = []
    else:
        auth_result = "auth_failed" if completed.returncode == 255 else "connection_failed"
        passed = False
        errors = [f"ssh_probe_exit_status_{completed.returncode}"]
    return LambdaSSHConnectivityProbeEvidence(
        probe_attempted=True,
        probe_completed=True,
        probe_passed=passed,
        auth_result=auth_result,
        owned_instance_id_redacted=redact_instance_id(owned_instance_id),
        target_host_redacted=host_discovery_result.host_redacted or "<redacted-host>",
        host_discovery_attempted=True,
        host_discovery_status=host_discovery_result.status,
        host_discovery_source_path=host_discovery_result.source_path,
        host_discovery_poll_count=host_discovery_result.poll_count,
        host_discovery_duration_seconds=host_discovery_result.duration_seconds,
        sanitized_metadata_keys=host_discovery_result.sanitized_metadata_keys,
        sanitized_metadata_key_paths=host_discovery_result.sanitized_metadata_key_paths,
        ssh_key_present=True,
        ssh_key_permissions_too_open=bool(private_key_path.stat().st_mode & 0o077),
        ssh_username=ssh_username,
        exit_status=completed.returncode,
        elapsed_seconds=elapsed,
        errors=errors,
    )


def extract_ssh_host_from_instance_payload(payload: dict[str, Any]) -> str | None:
    result = extract_ssh_host_from_instance_metadata(payload)
    return result.host if result.status == "FOUND" else None


def _real_ssh_command(
    *,
    host: str,
    private_key_path: Path,
    ssh_username: str,
) -> list[str]:
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "RequestTTY=no",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "ForwardAgent=no",
        "-o",
        "ForwardX11=no",
        "-o",
        "PermitLocalCommand=no",
        "-o",
        "ControlMaster=no",
        "-o",
        "SessionType=none",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "NumberOfPasswordPrompts=0",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ConnectionAttempts=1",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=1",
        "-N",
        "-T",
        "-i",
        str(private_key_path),
        f"{ssh_username}@{host}",
    ]


def write_lambda_ssh_connectivity_probe_evidence(
    path: str | Path,
    report: LambdaSSHConnectivityProbeEvidence,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
