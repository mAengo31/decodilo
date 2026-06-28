"""M061 whoami-only identity command planning and one-shot gates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.m061_whoami_authorization import (
    load_lambda_m061_whoami_authorization,
)
from decodilo.lambda_cloud.ssh_connectivity_m056_plan import (
    M056_SELECTED_CANDIDATE,
    M056_SELECTED_REGION,
)
from decodilo.lambda_cloud.ssh_hostname_identity_closeout import (
    load_lambda_ssh_hostname_identity_closeout,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot

M061_COMMAND = "whoami"
M061_ARMED_FOR = "m061_whoami_identity_command_single_launch_attempt"


class LambdaM061IdentityCommandPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M061"
    plan_status: Literal["plan_passed", "blocked"]
    selected_candidate: str | None = None
    selected_region: str | None = None
    selected_candidate_source: str | None = None
    selected_ssh_key_hash: str | None = None
    command: str = M061_COMMAND
    command_argv: list[str] = Field(default_factory=lambda: [M061_COMMAND])
    quantity: int = 1
    ssh_username: str = "ubuntu"
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    price_per_instance_hour: float | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    max_launch_attempts: int = 1
    max_ssh_connectivity_attempts: int = 1
    max_remote_command_attempts: int = 1
    response_capture_active: bool = True
    status_before_parse: bool = True
    no_auto_launch_retry: bool = True
    effective_launch_timeout_seconds: float = 30.0
    ssh_connectivity_only: bool = True
    remote_exec_allowed: bool = False
    interactive_shell_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    stdout_capture_allowed: bool = True
    stderr_capture_allowed: bool = True
    bounded_output_capture: bool = True
    redacted_output_capture: bool = True
    private_key_reference_available_for_probe: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM061IdentityCommandPlan:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.command != M061_COMMAND
            or self.command_argv != [M061_COMMAND]
            or self.quantity != 1
            or self.max_launch_attempts != 1
            or self.max_ssh_connectivity_attempts != 1
            or self.max_remote_command_attempts != 1
            or not self.no_auto_launch_retry
            or self.remote_exec_allowed
            or self.interactive_shell_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or self.package_install_allowed
            or self.training_allowed
            or self.setup_scripts_allowed
            or self.cloud_init_allowed
            or not self.stdout_capture_allowed
            or not self.stderr_capture_allowed
            or not self.bounded_output_capture
            or not self.redacted_output_capture
        ):
            raise ValueError("M061 identity command plan violates constraints")
        if self.plan_status == "plan_passed" and self.blockers:
            raise ValueError("passing M061 plan cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM061IdentityCommandGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M061"
    gate_passed: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    command: str = M061_COMMAND
    max_remote_commands: int = 1
    no_shell_wrapper: bool = True
    no_command_chaining: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_training: bool = True
    no_auto_retry: bool = True
    stdout_capture_bounded_redacted: bool = True
    stderr_capture_bounded_redacted: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_gate(self) -> LambdaM061IdentityCommandGateCheck:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.command != M061_COMMAND
            or self.max_remote_commands != 1
            or not self.no_shell_wrapper
            or not self.no_command_chaining
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_package_install
            or not self.no_training
            or not self.no_auto_retry
            or not self.stdout_capture_bounded_redacted
            or not self.stderr_capture_bounded_redacted
        ):
            raise ValueError("M061 gate violates whoami-only constraints")
        if self.gate_passed and self.blockers:
            raise ValueError("passing M061 gate cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM061OneShotArming(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    arming_id: str
    arming_status: Literal["not_armed", "armed_for_one_shot_m061_identity_command"]
    armed_for: str = M061_ARMED_FOR
    one_shot_request_send_permitted: bool = False
    request_send_permission_delegated_to_reviewer_bridge: bool = True
    selected_candidate: str | None = None
    selected_region: str | None = None
    approved_command: str = M061_COMMAND
    max_launch_attempts: int = 1
    max_ssh_connectivity_attempts: int = 1
    max_remote_command_attempts: int = 1
    no_auto_retry: bool = True
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
    def _validate_arming(self) -> LambdaM061OneShotArming:
        if (
            self.armed_for != M061_ARMED_FOR
            or self.one_shot_request_send_permitted
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.approved_command != M061_COMMAND
            or self.max_launch_attempts != 1
            or self.max_ssh_connectivity_attempts != 1
            or self.max_remote_command_attempts != 1
            or not self.no_auto_retry
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_package_install
            or not self.no_training
            or not self.terminate_owned_instance_required
            or not self.termination_verification_required
        ):
            raise ValueError("M061 arming violates one-shot constraints")
        if self.arming_status == "armed_for_one_shot_m061_identity_command" and self.blockers:
            raise ValueError("armed M061 artifact cannot have blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaM061ReviewerBridge(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    bridge_status: Literal["not_ready", "reviewer_compatible_one_shot_ready"]
    one_shot_request_send_permitted: bool
    one_shot_ssh_connectivity_probe_permitted: bool
    one_shot_minimal_remote_command_permitted: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    approved_command: str = M061_COMMAND
    max_launch_attempts: int = 1
    max_ssh_connectivity_attempts: int = 1
    max_remote_command_attempts: int = 1
    no_auto_retry: bool = True
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
    def _validate_bridge(self) -> LambdaM061ReviewerBridge:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.standing_launch_ready
            or self.standing_launch_allowed
            or self.approved_command != M061_COMMAND
            or self.max_launch_attempts != 1
            or self.max_remote_command_attempts != 1
            or not self.no_auto_retry
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_package_install
            or not self.no_training
        ):
            raise ValueError("M061 reviewer bridge violates one-shot constraints")
        if self.bridge_status == "reviewer_compatible_one_shot_ready":
            if (
                self.blockers
                or not self.one_shot_request_send_permitted
                or not self.one_shot_ssh_connectivity_probe_permitted
                or not self.one_shot_minimal_remote_command_permitted
            ):
                raise ValueError("ready M061 bridge requires one-shot permissions")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m061_identity_command_plan_from_paths(
    *,
    discovery_report: str | Path,
    authorization: str | Path,
    hostname_closeout: str | Path,
    ssh_key_selection: str | Path,
    price_snapshot: str | Path,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaM061IdentityCommandPlan:
    return build_lambda_m061_identity_command_plan(
        discovery=load_lambda_live_discovery_report(discovery_report),
        authorization_path=authorization,
        hostname_closeout_path=hostname_closeout,
        ssh_key_selection_path=ssh_key_selection,
        price_snapshot=load_price_snapshot(price_snapshot),
        max_budget=max_budget,
        planned_runtime_minutes=planned_runtime_minutes,
        safety_buffer_multiplier=safety_buffer_multiplier,
    )


def build_lambda_m061_identity_command_plan(
    *,
    discovery: LambdaLiveDiscoveryReport,
    authorization_path: str | Path,
    hostname_closeout_path: str | Path,
    ssh_key_selection_path: str | Path,
    price_snapshot: PriceSnapshot,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaM061IdentityCommandPlan:
    auth = load_lambda_m061_whoami_authorization(authorization_path)
    closeout = load_lambda_ssh_hostname_identity_closeout(hostname_closeout_path)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection_path)
    blockers: list[str] = []
    if (
        auth.authorization_status
        != "authorized_for_future_m061_whoami_identity_command_review"
    ):
        blockers.extend(auth.blockers or ["m061_authorization_not_ready"])
    if auth.selected_future_command_set != [M061_COMMAND]:
        blockers.append("m061_authorization_must_select_whoami_only")
    if not closeout.closeout_succeeded:
        blockers.extend(closeout.blockers or ["hostname_closeout_not_succeeded"])
    if closeout.command != "hostname":
        blockers.append("m061_requires_prior_hostname_closeout")
    if not discovery.live_api_used or not discovery.read_only_mode:
        blockers.append("fresh_live_read_only_discovery_required")
    if not discovery.required_endpoint_success:
        blockers.append("required_read_only_endpoint_failed")
    if discovery.summary.read_operations <= 0:
        blockers.append("read_only_discovery_must_have_read_operations")
    if discovery.summary.mutating_operations != 0:
        blockers.append("read_only_discovery_report_contains_mutation")
    if discovery.billable_action_performed:
        blockers.append("read_only_discovery_cannot_be_billable")
    if discovery.unmanaged_instances:
        blockers.append("unmanaged_instances_present")
    if not ssh.selection_passed:
        blockers.extend(ssh.errors or ["existing_ssh_key_selection_required"])
    if not ssh.selected_ssh_key_name_for_payload:
        blockers.append("raw_existing_ssh_key_name_missing_from_private_artifact")
    if ssh.raw_public_key_material_present:
        blockers.append("raw_public_key_material_present")
    live_item = _find_live_candidate(discovery)
    if live_item is None:
        blockers.append("m061_selected_candidate_not_live_available_in_us_east_1")
    record = _find_price_record(price_snapshot, M056_SELECTED_CANDIDATE)
    price_per_hour = (
        record.price_per_instance_hour
        if record is not None
        else (live_item.price_per_hour if live_item is not None else None)
    )
    if price_per_hour is None:
        blockers.append("selected_candidate_price_missing")
    estimated = _estimate(price_per_hour, planned_runtime_minutes)
    buffered = None if estimated is None else round(estimated * safety_buffer_multiplier, 8)
    if buffered is not None and buffered >= max_budget:
        blockers.append("buffered_estimated_cost_not_below_max_budget")
    return LambdaM061IdentityCommandPlan(
        plan_status="plan_passed" if not blockers else "blocked",
        selected_candidate=M056_SELECTED_CANDIDATE if live_item is not None else None,
        selected_region=M056_SELECTED_REGION if live_item is not None else None,
        selected_candidate_source="fresh_live_read_only_instance_types",
        selected_ssh_key_hash=ssh.selected_ssh_key_name_redacted_or_hash,
        gpu_type=(
            record.gpu_type
            if record is not None
            else (live_item.gpu_type if live_item is not None else None)
        ),
        gpus_per_instance=(
            record.gpus_per_instance
            if record is not None
            else (live_item.gpus if live_item is not None else None)
        ),
        price_per_instance_hour=price_per_hour,
        estimated_30min_cost=estimated,
        buffered_estimated_30min_cost=buffered,
        max_budget=max_budget,
        max_runtime_minutes=planned_runtime_minutes,
        blockers=sorted(set(blockers)),
        warnings=[
            "M061 plan is non-executable until a one-shot reviewer bridge is used",
            "selected candidate must be freshly live-available before request construction",
            "only the exact whoami command is in scope",
            "hostname, shell wrappers, GPU visibility, Python, and training remain forbidden",
        ],
    )


def build_lambda_m061_identity_command_gate_check_from_paths(
    *,
    plan: str | Path,
    authorization: str | Path,
) -> LambdaM061IdentityCommandGateCheck:
    plan_report = load_lambda_m061_identity_command_plan(plan)
    auth = load_lambda_m061_whoami_authorization(authorization)
    blockers = list(plan_report.blockers)
    if plan_report.plan_status != "plan_passed":
        blockers.append("m061_plan_not_passed")
    if (
        auth.authorization_status
        != "authorized_for_future_m061_whoami_identity_command_review"
    ):
        blockers.extend(auth.blockers or ["m061_authorization_not_ready"])
    if auth.selected_future_command_set != [M061_COMMAND]:
        blockers.append("m061_authorization_must_select_whoami_only")
    if plan_report.command != M061_COMMAND or plan_report.command_argv != [M061_COMMAND]:
        blockers.append("m061_plan_command_must_equal_whoami")
    if plan_report.max_remote_command_attempts != 1:
        blockers.append("max_remote_commands_must_equal_one")
    return LambdaM061IdentityCommandGateCheck(
        gate_passed=not blockers,
        selected_candidate=plan_report.selected_candidate,
        selected_region=plan_report.selected_region,
        blockers=sorted(set(blockers)),
        warnings=[
            "M061 gate permits exactly one remote command: whoami",
            (
                "shell wrappers, command chaining, transfer, install, GPU visibility, "
                "Python, and training remain forbidden"
            ),
        ],
    )


def build_lambda_m061_one_shot_arming_from_paths(
    *,
    gate_check: str | Path,
    response_loss_controls: str | Path,
    expires_minutes: int,
    created_at_utc: str | None = None,
) -> LambdaM061OneShotArming:
    from decodilo.lambda_cloud.strand_response_loss_control_check import (
        load_lambda_strand_response_loss_control_check,
    )

    paths = {
        "gate_check": str(gate_check),
        "response_loss_controls": str(response_loss_controls),
    }
    hashes = {name: _sha256_file(path) for name, path in paths.items() if Path(path).exists()}
    gate = load_lambda_m061_identity_command_gate_check(gate_check)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    blockers = list(gate.blockers)
    if not gate.gate_passed:
        blockers.append("m061_gate_not_passed")
    if not controls.controls_passed or not controls.no_auto_launch_retry:
        blockers.extend(controls.blockers or ["response_loss_controls_not_passed"])
    if expires_minutes <= 0:
        blockers.append("expiration_required")
    created = _parse_utc(created_at_utc) if created_at_utc else datetime.now(timezone.utc)
    expires = created + timedelta(minutes=expires_minutes)
    status: Literal["not_armed", "armed_for_one_shot_m061_identity_command"] = (
        "armed_for_one_shot_m061_identity_command" if not blockers else "not_armed"
    )
    arming_id = "m061-whoami-" + _hash_json(
        {
            "created_at_utc": _format_utc(created),
            "expires_at_utc": _format_utc(expires),
            "artifact_hashes": hashes,
            "selected_candidate": gate.selected_candidate,
            "selected_region": gate.selected_region,
        }
    )[:16]
    return LambdaM061OneShotArming(
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
            "M061 arming is preview-only; reviewer bridge exposes one-shot permission",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def build_lambda_m061_reviewer_bridge_from_path(
    *,
    arming: str | Path,
    now_utc: str | None = None,
) -> LambdaM061ReviewerBridge:
    arming_report = load_lambda_m061_one_shot_arming(arming)
    blockers = list(arming_report.blockers)
    if arming_report.arming_status != "armed_for_one_shot_m061_identity_command":
        blockers.append("m061_one_shot_arming_not_armed")
    if is_lambda_m061_one_shot_arming_expired(arming_report, now_utc=now_utc):
        blockers.append("m061_one_shot_arming_expired")
    status: Literal["not_ready", "reviewer_compatible_one_shot_ready"] = (
        "reviewer_compatible_one_shot_ready" if not blockers else "not_ready"
    )
    return LambdaM061ReviewerBridge(
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
            "M061 bridge is the only artifact exposing one-shot whoami permission",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def is_lambda_m061_one_shot_arming_expired(
    report: LambdaM061OneShotArming,
    *,
    now_utc: str | None = None,
) -> bool:
    now = _parse_utc(now_utc) if now_utc else datetime.now(timezone.utc)
    return now >= _parse_utc(report.expires_at_utc)


def load_lambda_m061_identity_command_plan(
    path: str | Path,
) -> LambdaM061IdentityCommandPlan:
    return LambdaM061IdentityCommandPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_m061_identity_command_gate_check(
    path: str | Path,
) -> LambdaM061IdentityCommandGateCheck:
    return LambdaM061IdentityCommandGateCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_m061_one_shot_arming(path: str | Path) -> LambdaM061OneShotArming:
    return LambdaM061OneShotArming.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_m061_reviewer_bridge(path: str | Path) -> LambdaM061ReviewerBridge:
    return LambdaM061ReviewerBridge.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m061_identity_command_plan(
    path: str | Path,
    report: LambdaM061IdentityCommandPlan,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_m061_identity_command_gate_check(
    path: str | Path,
    report: LambdaM061IdentityCommandGateCheck,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_m061_one_shot_arming(
    path: str | Path,
    report: LambdaM061OneShotArming,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_m061_reviewer_bridge(
    path: str | Path,
    report: LambdaM061ReviewerBridge,
) -> None:
    _write_json(path, report.to_json())


def m061_plan_hash(plan: LambdaM061IdentityCommandPlan) -> str:
    material = {
        "milestone": plan.milestone,
        "selected_candidate": plan.selected_candidate,
        "selected_region": plan.selected_region,
        "selected_ssh_key_hash": plan.selected_ssh_key_hash,
        "command": plan.command,
    }
    return _hash_json(material)


def _find_live_candidate(discovery: LambdaLiveDiscoveryReport):
    return next(
        (
            item
            for item in discovery.instance_types
            if (
                item.name == M056_SELECTED_CANDIDATE
                or item.instance_type_id == M056_SELECTED_CANDIDATE
            )
            and M056_SELECTED_REGION in item.regions
        ),
        None,
    )


def _find_price_record(
    price_snapshot: PriceSnapshot,
    shape: str,
) -> SnapshotPriceRecord | None:
    return next(
        (
            record
            for record in price_snapshot.records
            if record.provider == "lambda" and record.instance_type == shape
        ),
        None,
    )


def _estimate(price_per_hour: float | None, planned_runtime_minutes: int) -> float | None:
    if price_per_hour is None:
        return None
    return round(price_per_hour * planned_runtime_minutes / 60, 8)


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


def _write_json(path: str | Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
