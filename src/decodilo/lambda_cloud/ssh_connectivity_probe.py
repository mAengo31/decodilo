"""Bounded SSH connectivity/authentication probe for M054B."""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.real_launch_result import redact_instance_id
from decodilo.lambda_cloud.ssh_failure_classifier import classify_ssh_failure
from decodilo.lambda_cloud.ssh_failure_stderr_capture import redact_ssh_stderr
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
    "ssh_port_not_reachable",
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
    ssh_port_readiness_attempted: bool = False
    ssh_port_reachable: bool = False
    ssh_port_poll_count: int = 0
    ssh_port_wait_seconds: float = 0.0
    ssh_port_connect_timeout_seconds: float = 0.0
    stderr_capture_active: bool = True
    redacted_stderr_present: bool = False
    stderr_redacted: str | None = None
    stderr_sha256_prefix: str | None = None
    stderr_truncated: bool = False
    stderr_secret_scan_passed: bool = True
    stderr_redaction_patterns_applied: list[str] = Field(default_factory=list)
    ssh_failure_classification: str | None = None
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
            or not self.stderr_capture_active
            or not self.stderr_secret_scan_passed
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
    ssh_port_ready_timeout_seconds: float = 300.0,
    ssh_port_poll_interval_seconds: float = 5.0,
    ssh_port_connect_timeout_seconds: float = 3.0,
    tcp_connect_checker: Callable[[str, int, float], bool] | None = None,
    sleep_func: Callable[[float], None] = time.sleep,
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

    port_ready = _wait_for_ssh_port_ready(
        host=host_discovery_result.host,
        timeout_seconds=ssh_port_ready_timeout_seconds,
        interval_seconds=ssh_port_poll_interval_seconds,
        connect_timeout_seconds=ssh_port_connect_timeout_seconds,
        checker=tcp_connect_checker or _default_tcp_connect_checker,
        sleep_func=sleep_func,
    )
    if not port_ready.reachable:
        return LambdaSSHConnectivityProbeEvidence(
            probe_attempted=False,
            probe_completed=False,
            probe_passed=False,
            auth_result="ssh_port_not_reachable",
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
            ssh_port_readiness_attempted=True,
            ssh_port_reachable=False,
            ssh_port_poll_count=port_ready.poll_count,
            ssh_port_wait_seconds=port_ready.elapsed_seconds,
            ssh_port_connect_timeout_seconds=ssh_port_connect_timeout_seconds,
            blockers=["ssh_port_not_reachable"],
            warnings=[
                "SSH host was discovered, but TCP port 22 did not become reachable "
                "inside the bounded readiness window; SSH auth probe was skipped."
            ],
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
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        capture = _redacted_stderr_fields(
            stderr="",
            private_key_path=private_key_path,
            host=host_discovery_result.host,
        )
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
            ssh_port_readiness_attempted=True,
            ssh_port_reachable=True,
            ssh_port_poll_count=port_ready.poll_count,
            ssh_port_wait_seconds=port_ready.elapsed_seconds,
            ssh_port_connect_timeout_seconds=ssh_port_connect_timeout_seconds,
            elapsed_seconds=round(time.monotonic() - started, 6),
            **capture,
            warnings=[
                "OpenSSH -N/-T held the connection until the bounded local timeout; "
                "no remote command output was collected"
            ],
        )
    elapsed = round(time.monotonic() - started, 6)
    capture = _redacted_stderr_fields(
        stderr=completed.stderr or "",
        private_key_path=private_key_path,
        host=host_discovery_result.host,
    )
    classification = classify_ssh_failure(
        exit_code=completed.returncode,
        stderr_redacted=capture["stderr_redacted"],
        tcp_readiness_succeeded=True,
    )
    if completed.returncode == 0:
        auth_result: LambdaSSHConnectivityAuthResult = "auth_succeeded"
        passed = True
        errors: list[str] = []
        failure_classification = None
    else:
        auth_result = "auth_failed" if completed.returncode == 255 else "connection_failed"
        passed = False
        failure_classification = classification.classification
        errors = [
            f"ssh_probe_exit_status_{completed.returncode}",
            f"ssh_failure_classification_{classification.classification}",
        ]
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
        ssh_port_readiness_attempted=True,
        ssh_port_reachable=True,
        ssh_port_poll_count=port_ready.poll_count,
        ssh_port_wait_seconds=port_ready.elapsed_seconds,
        ssh_port_connect_timeout_seconds=ssh_port_connect_timeout_seconds,
        ssh_failure_classification=failure_classification,
        exit_status=completed.returncode,
        elapsed_seconds=elapsed,
        **capture,
        errors=errors,
        warnings=classification.warnings,
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
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={_isolated_known_hosts_path(host)}",
        "-o",
        "StrictHostKeyChecking=accept-new",
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


def _isolated_known_hosts_path(host: str) -> Path:
    digest = hashlib.sha256(host.encode("utf-8")).hexdigest()[:16]
    return Path("/tmp") / f"decodilo-lambda-ssh-known-hosts-{digest}"


def _redacted_stderr_fields(
    *,
    stderr: str,
    private_key_path: Path,
    host: str,
) -> dict[str, object]:
    capture = redact_ssh_stderr(
        stderr,
        private_key_path=str(private_key_path),
        host=host,
    )
    return {
        "redacted_stderr_present": bool(capture.stderr_redacted),
        "stderr_redacted": capture.stderr_redacted,
        "stderr_sha256_prefix": capture.stderr_sha256_prefix,
        "stderr_truncated": capture.stderr_truncated,
        "stderr_secret_scan_passed": capture.secret_scan_passed,
        "stderr_redaction_patterns_applied": capture.redaction_patterns_applied,
    }


class _SSHPortReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    reachable: bool
    poll_count: int
    elapsed_seconds: float


def _wait_for_ssh_port_ready(
    *,
    host: str,
    timeout_seconds: float,
    interval_seconds: float,
    connect_timeout_seconds: float,
    checker: Callable[[str, int, float], bool],
    sleep_func: Callable[[float], None],
) -> _SSHPortReadiness:
    started = time.monotonic()
    deadline = started + max(0.0, timeout_seconds)
    poll_count = 0
    while True:
        poll_count += 1
        if checker(host, 22, connect_timeout_seconds):
            return _SSHPortReadiness(
                reachable=True,
                poll_count=poll_count,
                elapsed_seconds=round(time.monotonic() - started, 6),
            )
        now = time.monotonic()
        if now >= deadline:
            return _SSHPortReadiness(
                reachable=False,
                poll_count=poll_count,
                elapsed_seconds=round(now - started, 6),
            )
        sleep_func(min(interval_seconds, max(0.0, deadline - now)))


def _default_tcp_connect_checker(host: str, port: int, timeout_seconds: float) -> bool:
    socket = importlib.import_module("socket")
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def write_lambda_ssh_connectivity_probe_evidence(
    path: str | Path,
    report: LambdaSSHConnectivityProbeEvidence,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
