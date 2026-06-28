"""M057 minimal SSH remote-command gate and evidence helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.gpu_visibility_command_policy import M063_GPU_VISIBILITY_COMMAND
from decodilo.lambda_cloud.python_runtime_command_policy import M065_PYTHON_RUNTIME_COMMAND
from decodilo.lambda_cloud.real_launch_result import redact_instance_id
from decodilo.lambda_cloud.ssh_connectivity_m056_gate_check import (
    load_lambda_ssh_connectivity_m056_gate_check,
)
from decodilo.lambda_cloud.ssh_connectivity_m056_plan import (
    M056_SELECTED_CANDIDATE,
    M056_SELECTED_REGION,
    load_lambda_ssh_connectivity_m056_plan,
)
from decodilo.lambda_cloud.ssh_connectivity_probe import (
    _default_tcp_connect_checker,
    _isolated_known_hosts_path,
    _redacted_stderr_fields,
    _wait_for_ssh_port_ready,
)
from decodilo.lambda_cloud.ssh_failure_classifier import classify_ssh_failure
from decodilo.lambda_cloud.ssh_failure_stderr_capture import (
    load_lambda_ssh_stderr_capture_policy,
)
from decodilo.lambda_cloud.ssh_host_discovery import (
    LambdaSSHHostDiscoveryResult,
    extract_ssh_host_from_instance_metadata,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)

M057_COMMAND = "true"
M059_IDENTITY_COMMAND = "hostname"
M061_IDENTITY_COMMAND = "whoami"
OUTPUT_CAPTURE_COMMANDS = {
    M059_IDENTITY_COMMAND,
    M061_IDENTITY_COMMAND,
    M063_GPU_VISIBILITY_COMMAND,
    M065_PYTHON_RUNTIME_COMMAND,
}
ALLOWED_MINIMAL_REMOTE_COMMANDS = {
    M057_COMMAND,
    M059_IDENTITY_COMMAND,
    M061_IDENTITY_COMMAND,
    M063_GPU_VISIBILITY_COMMAND,
    M065_PYTHON_RUNTIME_COMMAND,
}
M057_ARMED_FOR = "m057_minimal_remote_command_single_launch_attempt"


class LambdaM057OperatorApproval(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    approval_status: Literal[
        "not_provided",
        "approved_for_m057_minimal_remote_command",
    ]
    approved_command: str | None = None
    max_launch_attempts: int = 1
    max_remote_command_attempts: int = 1
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    interactive_shell_allowed: bool = False
    command_output_collection_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    package_install_allowed: bool = False
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    training_allowed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_approval(self) -> LambdaM057OperatorApproval:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.interactive_shell_allowed
            or self.command_output_collection_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or self.package_install_allowed
            or self.setup_scripts_allowed
            or self.cloud_init_allowed
            or self.training_allowed
        ):
            raise ValueError("M057 approval cannot permit broad remote work")
        if self.max_launch_attempts != 1 or self.max_remote_command_attempts != 1:
            raise ValueError("M057 approval must remain one-shot")
        if self.approval_status == "approved_for_m057_minimal_remote_command":
            if self.approved_command != M057_COMMAND or self.blockers:
                raise ValueError("M057 approval can only approve exact command true")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM057MinimalRemoteCommandPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    policy_status: Literal["policy_defined", "blocked"]
    command: str = M057_COMMAND
    command_argv: list[str] = Field(default_factory=lambda: [M057_COMMAND])
    max_command_attempts: int = 1
    bounded_timeout_seconds: int = 15
    stdout_collected: bool = False
    stderr_capture_allowed: bool = True
    stderr_capture_bounded: bool = True
    stderr_capture_redacted: bool = True
    interactive_shell_allowed: bool = False
    tty_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaM057MinimalRemoteCommandPolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.command != M057_COMMAND
            or self.command_argv != [M057_COMMAND]
            or self.max_command_attempts != 1
            or self.stdout_collected
            or not self.stderr_capture_allowed
            or not self.stderr_capture_bounded
            or not self.stderr_capture_redacted
            or self.interactive_shell_allowed
            or self.tty_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or self.package_install_allowed
            or self.training_allowed
        ):
            raise ValueError("M057 minimal command policy violates constraints")
        if self.policy_status == "policy_defined" and self.blockers:
            raise ValueError("passing M057 command policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM057GateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate_passed: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    ssh_username: str = "ubuntu"
    approved_command: str = M057_COMMAND
    max_launch_attempts: int = 1
    max_remote_command_attempts: int = 1
    no_auto_retry: bool = True
    response_capture_active: bool = True
    status_before_parse: bool = True
    stdout_collection_allowed: bool = False
    stderr_capture_active: bool = True
    interactive_shell_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_gate(self) -> LambdaM057GateCheck:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.approved_command != M057_COMMAND
            or self.max_launch_attempts != 1
            or self.max_remote_command_attempts != 1
            or not self.no_auto_retry
            or not self.response_capture_active
            or not self.status_before_parse
            or self.stdout_collection_allowed
            or not self.stderr_capture_active
            or self.interactive_shell_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or self.package_install_allowed
            or self.training_allowed
        ):
            raise ValueError("M057 gate violates minimal remote-command constraints")
        if self.gate_passed and self.blockers:
            raise ValueError("passing M057 gate cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM057OneShotArming(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    arming_id: str
    arming_status: Literal["not_armed", "armed_for_one_shot_m057_minimal_remote_command"]
    armed_for: str = M057_ARMED_FOR
    one_shot_request_send_permitted: bool = False
    request_send_permission_delegated_to_reviewer_bridge: bool = True
    selected_candidate: str | None = None
    selected_region: str | None = None
    approved_command: str = M057_COMMAND
    max_launch_attempts: int = 1
    max_ssh_connectivity_attempts: int = 1
    max_remote_command_attempts: int = 1
    no_auto_retry: bool = True
    no_arbitrary_remote_exec: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_training: bool = True
    terminate_owned_instance_required: bool = True
    termination_verification_required: bool = True
    created_at_utc: str
    expires_at_utc: str
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_arming(self) -> LambdaM057OneShotArming:
        if (
            self.armed_for != M057_ARMED_FOR
            or self.one_shot_request_send_permitted
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.approved_command != M057_COMMAND
            or self.max_launch_attempts != 1
            or self.max_remote_command_attempts != 1
            or not self.no_auto_retry
            or not self.no_arbitrary_remote_exec
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_package_install
            or not self.no_training
            or not self.terminate_owned_instance_required
            or not self.termination_verification_required
        ):
            raise ValueError("M057 arming violates one-shot constraints")
        if (
            self.arming_status == "armed_for_one_shot_m057_minimal_remote_command"
            and self.blockers
        ):
            raise ValueError("armed M057 artifact cannot have blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM057ReviewerBridge(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    bridge_status: Literal["not_ready", "reviewer_compatible_one_shot_ready"]
    one_shot_request_send_permitted: bool
    one_shot_ssh_connectivity_probe_permitted: bool
    one_shot_minimal_remote_command_permitted: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    approved_command: str = M057_COMMAND
    max_launch_attempts: int = 1
    max_ssh_connectivity_attempts: int = 1
    max_remote_command_attempts: int = 1
    no_auto_retry: bool = True
    no_remote_exec: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_training: bool = True
    standing_launch_ready: bool = False
    standing_launch_allowed: bool = False
    expires_at_utc: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_bridge(self) -> LambdaM057ReviewerBridge:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.standing_launch_ready
            or self.standing_launch_allowed
            or self.approved_command != M057_COMMAND
            or self.max_launch_attempts != 1
            or self.max_remote_command_attempts != 1
            or not self.no_auto_retry
            or not self.no_remote_exec
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_package_install
            or not self.no_training
        ):
            raise ValueError("M057 bridge violates one-shot constraints")
        if self.bridge_status == "reviewer_compatible_one_shot_ready":
            if (
                self.blockers
                or not self.one_shot_request_send_permitted
                or not self.one_shot_ssh_connectivity_probe_permitted
                or not self.one_shot_minimal_remote_command_permitted
            ):
                raise ValueError("ready M057 bridge requires one-shot permissions")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM057MinimalRemoteCommandEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    probe_attempted: bool = False
    probe_completed: bool = False
    probe_passed: bool = False
    auth_result: str = "not_attempted"
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
    remote_command_attempted: bool = False
    remote_command_result: str = "not_attempted"
    approved_command: str = M057_COMMAND
    command_output_collected: bool = False
    stdout_stored: bool = False
    stdout_capture_active: bool = False
    stdout_redacted: str | None = None
    stdout_sha256_prefix: str | None = None
    stdout_truncated: bool = False
    stdout_secret_scan_passed: bool = True
    stdout_redaction_patterns_applied: list[str] = Field(default_factory=list)
    stderr_capture_active: bool = True
    redacted_stderr_present: bool = False
    stderr_redacted: str | None = None
    stderr_sha256_prefix: str | None = None
    stderr_truncated: bool = False
    stderr_secret_scan_passed: bool = True
    stderr_redaction_patterns_applied: list[str] = Field(default_factory=list)
    ssh_failure_classification: str | None = None
    client_mode: str = "openssh_batch_mode_exact_remote_command"
    bounded_timeout_seconds: int = 15
    exit_status: int | None = None
    elapsed_seconds: float = 0.0
    interactive_shell_attempted: bool = False
    file_transfer_attempted: bool = False
    port_forwarding_attempted: bool = False
    package_install_attempted: bool = False
    training_attempted: bool = False
    retry_attempted: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_evidence(self) -> LambdaM057MinimalRemoteCommandEvidence:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.approved_command not in ALLOWED_MINIMAL_REMOTE_COMMANDS
            or (
                self.command_output_collected
                and self.approved_command not in OUTPUT_CAPTURE_COMMANDS
            )
            or self.stdout_stored
            or not self.stdout_secret_scan_passed
            or not self.stderr_capture_active
            or not self.stderr_secret_scan_passed
            or self.interactive_shell_attempted
            or self.file_transfer_attempted
            or self.port_forwarding_attempted
            or self.package_install_attempted
            or self.training_attempted
            or self.retry_attempted
        ):
            raise ValueError("M057 evidence violates minimal remote-command constraints")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m057_operator_approval(
    *,
    acknowledge_all: bool = False,
) -> LambdaM057OperatorApproval:
    approved = bool(acknowledge_all)
    return LambdaM057OperatorApproval(
        approval_status=(
            "approved_for_m057_minimal_remote_command" if approved else "not_provided"
        ),
        approved_command=M057_COMMAND if approved else None,
        blockers=[] if approved else ["operator_approval_not_provided"],
        warnings=[
            "M057 approval permits exactly one bounded remote command: true",
            "approval does not permit shell, output collection, install, or training",
        ],
    )


def build_lambda_m057_minimal_remote_command_policy() -> LambdaM057MinimalRemoteCommandPolicy:
    return LambdaM057MinimalRemoteCommandPolicy(
        policy_status="policy_defined",
        warnings=[
            "exact remote command is true",
            "stdout is discarded and only bounded redacted stderr may be persisted",
        ],
    )


def build_lambda_m057_gate_check_from_paths(
    *,
    m056_plan: str | Path,
    m056_gate_check: str | Path,
    operator_approval: str | Path,
    command_policy: str | Path,
    stderr_capture_policy: str | Path,
) -> LambdaM057GateCheck:
    plan = load_lambda_ssh_connectivity_m056_plan(m056_plan)
    gate = load_lambda_ssh_connectivity_m056_gate_check(m056_gate_check)
    approval = load_lambda_m057_operator_approval(operator_approval)
    policy = load_lambda_m057_minimal_remote_command_policy(command_policy)
    stderr_policy = load_lambda_ssh_stderr_capture_policy(stderr_capture_policy)
    blockers: list[str] = []
    if plan.plan_status != "plan_passed":
        blockers.extend(plan.blockers or ["m056_plan_not_passed"])
    if plan.selected_candidate != M056_SELECTED_CANDIDATE:
        blockers.append("m057_requires_gpu_1x_a10")
    if plan.selected_region != M056_SELECTED_REGION:
        blockers.append("m057_requires_us_east_1")
    if not gate.gate_passed:
        blockers.extend(gate.blockers or ["m056_gate_not_passed"])
    if approval.approval_status != "approved_for_m057_minimal_remote_command":
        blockers.extend(approval.blockers or ["m057_operator_approval_missing"])
    if approval.approved_command != M057_COMMAND:
        blockers.append("m057_approval_must_be_exact_true")
    if policy.policy_status != "policy_defined":
        blockers.extend(policy.blockers or ["m057_command_policy_not_defined"])
    if policy.command != M057_COMMAND or policy.command_argv != [M057_COMMAND]:
        blockers.append("m057_command_policy_must_be_exact_true")
    if stderr_policy.capture_policy_status != "policy_defined":
        blockers.extend(stderr_policy.blockers or ["stderr_capture_policy_not_defined"])
    if not stderr_policy.secret_scan_passed:
        blockers.append("stderr_capture_policy_secret_scan_failed")
    return LambdaM057GateCheck(
        gate_passed=not blockers,
        selected_candidate=plan.selected_candidate,
        selected_region=plan.selected_region,
        ssh_username=plan.ssh_username,
        response_capture_active=plan.response_capture_active,
        status_before_parse=plan.status_before_parse,
        stderr_capture_active=stderr_policy.capture_policy_status == "policy_defined",
        blockers=sorted(set(blockers)),
        warnings=[
            "M057 gate permits exactly one remote command: true",
            "M057 gate does not permit shell, command exploration, installs, or training",
        ],
    )


def build_lambda_m057_one_shot_arming_from_paths(
    *,
    gate_check: str | Path,
    response_loss_controls: str | Path,
    expires_minutes: int,
    created_at_utc: str | None = None,
) -> LambdaM057OneShotArming:
    paths = {
        "gate_check": str(gate_check),
        "response_loss_controls": str(response_loss_controls),
    }
    hashes = {name: _sha256_file(path) for name, path in paths.items() if Path(path).exists()}
    gate = load_lambda_m057_gate_check(gate_check)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    blockers = list(gate.blockers)
    if not gate.gate_passed:
        blockers.append("m057_gate_not_passed")
    if not controls.controls_passed or not controls.no_auto_launch_retry:
        blockers.extend(controls.blockers or ["response_loss_controls_not_passed"])
    if expires_minutes <= 0:
        blockers.append("expiration_required")
    created = _parse_utc(created_at_utc) if created_at_utc else datetime.now(timezone.utc)
    expires = created + timedelta(minutes=expires_minutes)
    status: Literal["not_armed", "armed_for_one_shot_m057_minimal_remote_command"] = (
        "armed_for_one_shot_m057_minimal_remote_command" if not blockers else "not_armed"
    )
    arming_id = "m057-minimal-command-" + _hash_json(
        {
            "created_at_utc": _format_utc(created),
            "expires_at_utc": _format_utc(expires),
            "artifact_hashes": hashes,
            "selected_candidate": gate.selected_candidate,
            "selected_region": gate.selected_region,
        }
    )[:16]
    return LambdaM057OneShotArming(
        arming_id=arming_id,
        arming_status=status,
        selected_candidate=gate.selected_candidate,
        selected_region=gate.selected_region,
        created_at_utc=_format_utc(created),
        expires_at_utc=_format_utc(expires),
        artifact_hashes=hashes,
        artifact_paths=paths,
        blockers=sorted(set(blockers)),
        warnings=[
            "M057 arming is preview-only; reviewer bridge exposes one-shot permission",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def build_lambda_m057_reviewer_bridge_from_path(
    *,
    arming: str | Path,
    now_utc: str | None = None,
) -> LambdaM057ReviewerBridge:
    arming_report = load_lambda_m057_one_shot_arming(arming)
    blockers = list(arming_report.blockers)
    if arming_report.arming_status != "armed_for_one_shot_m057_minimal_remote_command":
        blockers.append("m057_one_shot_arming_not_armed")
    if is_lambda_m057_one_shot_arming_expired(arming_report, now_utc=now_utc):
        blockers.append("m057_one_shot_arming_expired")
    status: Literal["not_ready", "reviewer_compatible_one_shot_ready"] = (
        "reviewer_compatible_one_shot_ready" if not blockers else "not_ready"
    )
    return LambdaM057ReviewerBridge(
        bridge_status=status,
        one_shot_request_send_permitted=status == "reviewer_compatible_one_shot_ready",
        one_shot_ssh_connectivity_probe_permitted=(
            status == "reviewer_compatible_one_shot_ready"
        ),
        one_shot_minimal_remote_command_permitted=(
            status == "reviewer_compatible_one_shot_ready"
        ),
        selected_candidate=arming_report.selected_candidate,
        selected_region=arming_report.selected_region,
        expires_at_utc=arming_report.expires_at_utc,
        blockers=sorted(set(blockers)),
        warnings=[
            "M057 bridge is the only artifact exposing one-shot command permission",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def is_lambda_m057_one_shot_arming_expired(
    report: LambdaM057OneShotArming,
    *,
    now_utc: str | None = None,
) -> bool:
    now = _parse_utc(now_utc) if now_utc else datetime.now(timezone.utc)
    return now >= _parse_utc(report.expires_at_utc)


def run_lambda_m057_minimal_remote_command(
    *,
    owned_instance_id: str,
    instance_payload: dict[str, Any],
    private_key_path: Path | None,
    ssh_username: str = "ubuntu",
    timeout_seconds: int = 15,
    ssh_port_ready_timeout_seconds: float = 300.0,
    ssh_port_poll_interval_seconds: float = 5.0,
    ssh_port_connect_timeout_seconds: float = 3.0,
    fake_mode: bool = False,
    host_discovery_result: LambdaSSHHostDiscoveryResult | None = None,
    approved_command: str = M057_COMMAND,
    collect_stdout: bool = False,
) -> LambdaM057MinimalRemoteCommandEvidence:
    if approved_command not in ALLOWED_MINIMAL_REMOTE_COMMANDS:
        raise ValueError("minimal remote command must be an approved literal")
    if collect_stdout and approved_command not in OUTPUT_CAPTURE_COMMANDS:
            raise ValueError("stdout capture is only approved for reviewed commands")
    if host_discovery_result is None:
        host_discovery_result = extract_ssh_host_from_instance_metadata(instance_payload)
    if host_discovery_result.status != "FOUND" or not host_discovery_result.host:
        return LambdaM057MinimalRemoteCommandEvidence(
            owned_instance_id_redacted=redact_instance_id(owned_instance_id),
            auth_result="host_discovery_failed",
            approved_command=approved_command,
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
        return LambdaM057MinimalRemoteCommandEvidence(
            probe_attempted=True,
            probe_completed=True,
            probe_passed=True,
            auth_result="remote_command_succeeded",
            remote_command_attempted=True,
            remote_command_result="succeeded",
            approved_command=approved_command,
            command_output_collected=collect_stdout,
            stdout_capture_active=collect_stdout,
            stdout_redacted=(
                _stdout_redaction_label(approved_command) if collect_stdout else None
            ),
            stdout_sha256_prefix=(
                hashlib.sha256(f"fake-{approved_command}\n".encode()).hexdigest()[
                    :16
                ]
                if collect_stdout
                else None
            ),
            stdout_redaction_patterns_applied=(
                [f"{approved_command}_output_redacted"] if collect_stdout else []
            ),
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
            ssh_port_readiness_attempted=True,
            ssh_port_reachable=True,
            warnings=["fake-server mode did not open an SSH socket"],
        )
    if private_key_path is None or not private_key_path.is_file():
        return LambdaM057MinimalRemoteCommandEvidence(
            owned_instance_id_redacted=redact_instance_id(owned_instance_id),
            auth_result="ssh_key_missing",
            approved_command=approved_command,
            host_discovery_attempted=True,
            host_discovery_status=host_discovery_result.status,
            host_discovery_source_path=host_discovery_result.source_path,
            host_discovery_poll_count=host_discovery_result.poll_count,
            host_discovery_duration_seconds=host_discovery_result.duration_seconds,
            sanitized_metadata_keys=host_discovery_result.sanitized_metadata_keys,
            sanitized_metadata_key_paths=host_discovery_result.sanitized_metadata_key_paths,
            blockers=["ssh_key_missing"],
        )
    port_ready = _wait_for_ssh_port_ready(
        host=host_discovery_result.host,
        timeout_seconds=ssh_port_ready_timeout_seconds,
        interval_seconds=ssh_port_poll_interval_seconds,
        connect_timeout_seconds=ssh_port_connect_timeout_seconds,
        checker=_default_tcp_connect_checker,
        sleep_func=time.sleep,
    )
    if not port_ready.reachable:
        return LambdaM057MinimalRemoteCommandEvidence(
            owned_instance_id_redacted=redact_instance_id(owned_instance_id),
            auth_result="ssh_port_not_reachable",
            approved_command=approved_command,
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
        )
    command = _real_m057_ssh_command(
        host=host_discovery_result.host,
        private_key_path=private_key_path,
        ssh_username=ssh_username,
        approved_command=approved_command,
    )
    started = time.monotonic()
    try:
        completed = subprocess.run(  # noqa: S603 - argv is statically built.
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if collect_stdout else subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        timeout = False
    except subprocess.TimeoutExpired as exc:
        completed = subprocess.CompletedProcess(command, 255, "", exc.stderr or "")
        timeout = True
    elapsed = round(time.monotonic() - started, 6)
    capture = _redacted_stderr_fields(
        stderr=completed.stderr or "",
        private_key_path=private_key_path,
        host=host_discovery_result.host,
    )
    stdout_capture = _redacted_stdout_fields(
        stdout=completed.stdout or "",
        enabled=collect_stdout,
        approved_command=approved_command,
    )
    classification = classify_ssh_failure(
        exit_code=completed.returncode,
        stderr_redacted=capture["stderr_redacted"],
        tcp_readiness_succeeded=True,
    )
    passed = completed.returncode == 0 and not timeout
    errors: list[str] = []
    warnings = list(classification.warnings)
    if timeout:
        errors.append("m057_remote_command_timeout")
    elif completed.returncode != 0:
        errors.extend(
            [
                f"ssh_probe_exit_status_{completed.returncode}",
                f"ssh_failure_classification_{classification.classification}",
            ]
        )
    return LambdaM057MinimalRemoteCommandEvidence(
        probe_attempted=True,
        probe_completed=not timeout,
        probe_passed=passed,
        auth_result="remote_command_succeeded" if passed else "remote_command_failed",
        remote_command_attempted=True,
        remote_command_result="succeeded" if passed else "failed",
        approved_command=approved_command,
        command_output_collected=collect_stdout,
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
        ssh_failure_classification=None if passed else classification.classification,
        exit_status=completed.returncode,
        elapsed_seconds=elapsed,
        errors=errors,
        warnings=warnings,
        **capture,
        **stdout_capture,
    )


def _real_m057_ssh_command(
    *,
    host: str,
    private_key_path: Path,
    ssh_username: str,
    approved_command: str = M057_COMMAND,
) -> list[str]:
    if approved_command not in ALLOWED_MINIMAL_REMOTE_COMMANDS:
        raise ValueError("minimal remote command must be an approved literal")
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
        "-T",
        "-i",
        str(private_key_path),
        f"{ssh_username}@{host}",
        approved_command,
    ]


def _redacted_stdout_fields(
    *,
    stdout: str,
    enabled: bool,
    approved_command: str = M059_IDENTITY_COMMAND,
) -> dict[str, object]:
    if not enabled:
        return {
            "stdout_capture_active": False,
            "stdout_redacted": None,
            "stdout_sha256_prefix": None,
            "stdout_truncated": False,
            "stdout_secret_scan_passed": True,
            "stdout_redaction_patterns_applied": [],
        }
    raw = stdout.encode("utf-8", errors="replace")
    truncated = len(raw) > 4096
    return {
        "stdout_capture_active": True,
        "stdout_redacted": _stdout_redaction_label(approved_command) if stdout else "",
        "stdout_sha256_prefix": hashlib.sha256(raw).hexdigest()[:16],
        "stdout_truncated": truncated,
        "stdout_secret_scan_passed": True,
        "stdout_redaction_patterns_applied": [f"{approved_command}_output_redacted"],
    }


def _stdout_redaction_label(approved_command: str) -> str:
    if approved_command == M059_IDENTITY_COMMAND:
        return "<redacted-hostname>"
    if approved_command == M061_IDENTITY_COMMAND:
        return "<redacted-whoami>"
    if approved_command == M063_GPU_VISIBILITY_COMMAND:
        return "<redacted-gpu-visibility>"
    if approved_command == M065_PYTHON_RUNTIME_COMMAND:
        return "<redacted-python-version>"
    return "<redacted-output>"


def write_lambda_m057_operator_approval(
    path: str | Path,
    report: LambdaM057OperatorApproval,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_m057_minimal_remote_command_policy(
    path: str | Path,
    report: LambdaM057MinimalRemoteCommandPolicy,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_m057_gate_check(path: str | Path, report: LambdaM057GateCheck) -> None:
    _write_json(path, report.to_json())


def write_lambda_m057_one_shot_arming(
    path: str | Path,
    report: LambdaM057OneShotArming,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_m057_reviewer_bridge(
    path: str | Path,
    report: LambdaM057ReviewerBridge,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_m057_minimal_remote_command_evidence(
    path: str | Path,
    report: LambdaM057MinimalRemoteCommandEvidence,
) -> None:
    _write_json(path, report.to_json())


def load_lambda_m057_operator_approval(path: str | Path) -> LambdaM057OperatorApproval:
    return LambdaM057OperatorApproval.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_m057_minimal_remote_command_policy(
    path: str | Path,
) -> LambdaM057MinimalRemoteCommandPolicy:
    return LambdaM057MinimalRemoteCommandPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_m057_gate_check(path: str | Path) -> LambdaM057GateCheck:
    return LambdaM057GateCheck.model_validate_json(Path(path).read_text(encoding="utf-8"))


def load_lambda_m057_one_shot_arming(path: str | Path) -> LambdaM057OneShotArming:
    return LambdaM057OneShotArming.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_m057_reviewer_bridge(path: str | Path) -> LambdaM057ReviewerBridge:
    return LambdaM057ReviewerBridge.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def _write_json(path: str | Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _hash_json(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)
