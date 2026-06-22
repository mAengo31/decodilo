"""M056 live-candidate SSH diagnostic retry plan."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.ssh_failure_stderr_capture import (
    load_lambda_ssh_stderr_capture_policy,
)
from decodilo.lambda_cloud.ssh_host_key_policy import load_lambda_ssh_host_key_policy
from decodilo.lambda_cloud.ssh_identity_policy import load_lambda_ssh_identity_policy
from decodilo.lambda_cloud.ssh_private_key_file_policy import (
    load_lambda_ssh_private_key_file_policy,
)
from decodilo.lambda_cloud.ssh_retry_future_authorization import (
    load_lambda_ssh_retry_future_authorization,
)
from decodilo.lambda_cloud.ssh_username_policy import load_lambda_ssh_username_policy
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot

M056_SELECTED_CANDIDATE = "gpu_1x_a10"
M056_SELECTED_REGION = "us-east-1"

LambdaSSHConnectivityM056PlanStatus = Literal["plan_passed", "blocked"]


class LambdaSSHConnectivityM056Plan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M056"
    ssh_connectivity_path_used: bool = True
    plan_status: LambdaSSHConnectivityM056PlanStatus
    selected_candidate: str | None = None
    selected_region: str | None = None
    selected_candidate_source: str | None = None
    quantity: int = 1
    selected_ssh_key_hash: str | None = None
    ssh_username: str = "ubuntu"
    private_key_reference_source: str = "operator_env_private_key_reference"
    private_key_reference_available_for_probe: bool = True
    private_key_reference_public: str = "<redacted-private-key-reference>"
    identities_only: bool = True
    isolated_known_hosts: bool = True
    strict_host_key_checking_policy: str = "accept-new"
    stderr_capture_enabled: bool = True
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    price_per_instance_hour: float | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    max_launch_attempts: int = 1
    max_ssh_connectivity_attempts: int = 1
    response_capture_active: bool = True
    status_before_parse: bool = True
    no_auto_launch_retry: bool = True
    strand_payload_compatible: bool = True
    effective_launch_timeout_seconds: float = 30.0
    effective_terminate_timeout_seconds: float = 30.0
    effective_read_only_verification_timeout_seconds: float = 30.0
    ssh_connectivity_only: bool = True
    ssh_attempted: bool = False
    remote_command_attempted: bool = False
    file_transfer_attempted: bool = False
    port_forwarding_attempted: bool = False
    package_install_attempted: bool = False
    training_attempted: bool = False
    remote_exec_allowed: bool = False
    interactive_shell_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    old_path_fallback_blocked: bool = True
    m039_path_fallback_blocked: bool = True
    m054b_path_fallback_blocked: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHConnectivityM056Plan:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.remote_command_attempted
            or self.file_transfer_attempted
            or self.port_forwarding_attempted
            or self.package_install_attempted
            or self.training_attempted
            or self.remote_exec_allowed
            or self.interactive_shell_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or self.package_install_allowed
            or self.training_allowed
            or self.setup_scripts_allowed
            or self.cloud_init_allowed
            or not self.identities_only
            or not self.isolated_known_hosts
            or not self.stderr_capture_enabled
            or not self.no_auto_launch_retry
        ):
            raise ValueError("M056 plan violates one-shot SSH diagnostic constraints")
        if self.max_launch_attempts != 1 or self.max_ssh_connectivity_attempts != 1:
            raise ValueError("M056 plan must remain one-shot")
        if self.plan_status == "plan_passed" and self.blockers:
            raise ValueError("passing M056 plan cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_connectivity_m056_plan_from_paths(
    *,
    discovery_report: str | Path,
    authorization: str | Path,
    username_policy: str | Path,
    host_key_policy: str | Path,
    identity_policy: str | Path,
    private_key_file_policy: str | Path,
    stderr_capture_policy: str | Path,
    ssh_key_selection: str | Path,
    price_snapshot: str | Path,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaSSHConnectivityM056Plan:
    return build_lambda_ssh_connectivity_m056_plan(
        discovery=load_lambda_live_discovery_report(discovery_report),
        authorization_path=authorization,
        username_policy_path=username_policy,
        host_key_policy_path=host_key_policy,
        identity_policy_path=identity_policy,
        private_key_file_policy_path=private_key_file_policy,
        stderr_capture_policy_path=stderr_capture_policy,
        ssh_key_selection_path=ssh_key_selection,
        price_snapshot=load_price_snapshot(price_snapshot),
        max_budget=max_budget,
        planned_runtime_minutes=planned_runtime_minutes,
        safety_buffer_multiplier=safety_buffer_multiplier,
    )


def build_lambda_ssh_connectivity_m056_plan(
    *,
    discovery: LambdaLiveDiscoveryReport,
    authorization_path: str | Path,
    username_policy_path: str | Path,
    host_key_policy_path: str | Path,
    identity_policy_path: str | Path,
    private_key_file_policy_path: str | Path,
    stderr_capture_policy_path: str | Path,
    ssh_key_selection_path: str | Path,
    price_snapshot: PriceSnapshot,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaSSHConnectivityM056Plan:
    auth = load_lambda_ssh_retry_future_authorization(authorization_path)
    username = load_lambda_ssh_username_policy(username_policy_path)
    host_key = load_lambda_ssh_host_key_policy(host_key_policy_path)
    identity = load_lambda_ssh_identity_policy(identity_policy_path)
    key_file = load_lambda_ssh_private_key_file_policy(private_key_file_policy_path)
    stderr_policy = load_lambda_ssh_stderr_capture_policy(stderr_capture_policy_path)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection_path)
    blockers: list[str] = []
    warnings = [
        "M056 plan is non-executable until the one-shot reviewer bridge is used",
        "selected candidate must be freshly live-available before request construction",
        "bounded redacted stderr capture is required for SSH failure classification",
    ]
    if (
        auth.authorization_status
        != "authorized_for_future_m056_live_candidate_ssh_retry_review"
    ):
        blockers.extend(auth.blockers or ["m056_authorization_not_ready"])
    if auth.selected_candidate != M056_SELECTED_CANDIDATE:
        blockers.append("m056_authorization_candidate_mismatch")
    if auth.selected_region != M056_SELECTED_REGION:
        blockers.append("m056_authorization_region_mismatch")
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
    if username.username_policy_status != "policy_defined":
        blockers.extend(username.blockers or ["username_policy_not_defined"])
    if username.selected_username != "ubuntu":
        blockers.append("m056_requires_ubuntu_username")
    if host_key.host_key_policy_status != "policy_defined":
        blockers.extend(host_key.blockers or ["host_key_policy_not_defined"])
    if not host_key.isolated_known_hosts_file or host_key.strict_host_key_checking_no:
        blockers.append("isolated_known_hosts_accept_new_policy_required")
    if identity.identity_policy_status != "policy_defined":
        blockers.extend(identity.blockers or ["identity_policy_not_defined"])
    if not identity.identities_only_required or identity.identity_file_reference_count != 1:
        blockers.append("exactly_one_identities_only_key_required")
    if key_file.private_key_file_policy_status != "policy_defined":
        blockers.extend(key_file.blockers or ["private_key_file_policy_not_defined"])
    if stderr_policy.capture_policy_status != "policy_defined":
        blockers.extend(stderr_policy.blockers or ["stderr_capture_policy_not_defined"])
    if not stderr_policy.secret_scan_passed:
        blockers.append("stderr_capture_policy_secret_scan_failed")
    if not ssh.selection_passed:
        blockers.extend(ssh.errors or ["existing_ssh_key_selection_required"])
    if not ssh.selected_ssh_key_name_for_payload:
        blockers.append("raw_existing_ssh_key_name_missing_from_private_artifact")
    if ssh.raw_public_key_material_present:
        blockers.append("raw_public_key_material_present")
    if planned_runtime_minutes > 30:
        blockers.append("planned_runtime_exceeds_30_minutes")

    live_item = _find_live_candidate(discovery)
    if live_item is None:
        blockers.append("m056_selected_candidate_not_live_available_in_us_east_1")
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

    return LambdaSSHConnectivityM056Plan(
        plan_status="plan_passed" if not blockers else "blocked",
        selected_candidate=M056_SELECTED_CANDIDATE if live_item is not None else None,
        selected_region=M056_SELECTED_REGION if live_item is not None else None,
        selected_candidate_source="fresh_live_read_only_instance_types",
        selected_ssh_key_hash=ssh.selected_ssh_key_name_redacted_or_hash,
        ssh_username=username.selected_username or "ubuntu",
        identities_only=identity.identities_only_required,
        isolated_known_hosts=host_key.isolated_known_hosts_file,
        strict_host_key_checking_policy=host_key.strict_host_key_checking_policy,
        stderr_capture_enabled=stderr_policy.capture_policy_status == "policy_defined",
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
        warnings=warnings,
    )


def m056_plan_hash(plan: LambdaSSHConnectivityM056Plan) -> str:
    material = {
        "milestone": plan.milestone,
        "selected_candidate": plan.selected_candidate,
        "selected_region": plan.selected_region,
        "selected_ssh_key_hash": plan.selected_ssh_key_hash,
        "ssh_connectivity_only": plan.ssh_connectivity_only,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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


def load_lambda_ssh_connectivity_m056_plan(
    path: str | Path,
) -> LambdaSSHConnectivityM056Plan:
    return LambdaSSHConnectivityM056Plan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_m056_plan(
    path: str | Path,
    report: LambdaSSHConnectivityM056Plan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
