"""M054B SSH-connectivity launch/probe plan."""

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
from decodilo.lambda_cloud.m051_metadata_bootstrap_plan import (
    LambdaM051MetadataBootstrapPlan,
    load_lambda_m051_metadata_bootstrap_plan,
)
from decodilo.lambda_cloud.ssh_connectivity_execution_plan import (
    load_lambda_ssh_connectivity_execution_plan,
)
from decodilo.lambda_cloud.ssh_connectivity_static_validator import (
    load_lambda_ssh_connectivity_static_validation,
)
from decodilo.lambda_cloud.ssh_private_key_reference_policy import (
    load_lambda_ssh_private_key_reference_policy,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot

LambdaSSHConnectivityM054BPlanStatus = Literal["plan_passed", "blocked"]


class LambdaSSHConnectivityM054BPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    ssh_connectivity_path_used: bool = True
    plan_status: LambdaSSHConnectivityM054BPlanStatus
    selected_candidate: str | None = None
    selected_region: str | None = None
    selected_candidate_source: str | None = None
    quantity: int = 1
    selected_ssh_key_hash: str | None = None
    ssh_username: str = "ubuntu"
    private_key_reference_source: str = "approved_default_key_lookup"
    private_key_reference_available_for_probe: bool = False
    private_key_reference_public: str = "<redacted-private-key-reference>"
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
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHConnectivityM054BPlan:
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
        ):
            raise ValueError("M054B plan cannot enable unsafe SSH or launch flags")
        if self.plan_status == "plan_passed" and self.blockers:
            raise ValueError("passing M054B plan cannot carry blockers")
        if self.max_launch_attempts != 1 or self.max_ssh_connectivity_attempts != 1:
            raise ValueError("M054B plan must remain one-shot")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_connectivity_m054b_plan_from_paths(
    *,
    discovery_report: str | Path,
    execution_plan: str | Path,
    private_key_policy: str | Path,
    static_validation: str | Path,
    price_snapshot: str | Path,
    ssh_key_selection: str | Path,
    preferred_metadata_plan: str | Path | None = None,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaSSHConnectivityM054BPlan:
    preferred = (
        load_lambda_m051_metadata_bootstrap_plan(preferred_metadata_plan)
        if preferred_metadata_plan is not None and Path(preferred_metadata_plan).exists()
        else None
    )
    return build_lambda_ssh_connectivity_m054b_plan(
        discovery=load_lambda_live_discovery_report(discovery_report),
        execution_plan_path=execution_plan,
        private_key_policy_path=private_key_policy,
        static_validation_path=static_validation,
        price_snapshot=load_price_snapshot(price_snapshot),
        ssh_key_selection_path=ssh_key_selection,
        preferred_metadata_plan=preferred,
        max_budget=max_budget,
        planned_runtime_minutes=planned_runtime_minutes,
        safety_buffer_multiplier=safety_buffer_multiplier,
    )


def build_lambda_ssh_connectivity_m054b_plan(
    *,
    discovery: LambdaLiveDiscoveryReport,
    execution_plan_path: str | Path,
    private_key_policy_path: str | Path,
    static_validation_path: str | Path,
    price_snapshot: PriceSnapshot,
    ssh_key_selection_path: str | Path,
    preferred_metadata_plan: LambdaM051MetadataBootstrapPlan | None = None,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaSSHConnectivityM054BPlan:
    execution_plan = load_lambda_ssh_connectivity_execution_plan(execution_plan_path)
    key_policy = load_lambda_ssh_private_key_reference_policy(private_key_policy_path)
    static = load_lambda_ssh_connectivity_static_validation(static_validation_path)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection_path)
    blockers: list[str] = []
    warnings = [
        "M054B plan is still non-executable until m029 run arms it",
        "private key material is not serialized; default lookup is local only",
    ]

    if execution_plan.plan_status != "plan_defined":
        blockers.extend(execution_plan.blockers or ["execution_plan_not_defined"])
    if key_policy.key_reference_policy_status != "policy_defined":
        blockers.extend(key_policy.blockers or ["private_key_policy_not_defined"])
    if not static.static_validation_passed:
        blockers.extend(static.blockers or ["static_validation_not_passed"])
    if not discovery.live_api_used or not discovery.read_only_mode:
        blockers.append("fresh_live_read_only_discovery_required")
    if not discovery.required_endpoint_success:
        blockers.append("required_read_only_endpoint_failed")
    if discovery.summary.mutating_operations != 0:
        blockers.append("read_only_discovery_report_contains_mutation")
    if discovery.billable_action_performed:
        blockers.append("read_only_discovery_cannot_be_billable")
    if discovery.unmanaged_instances:
        blockers.append("unmanaged_instances_present")
    if price_snapshot.is_sample_data:
        blockers.append("sample_price_snapshot_cannot_authorize_m054b")
    if not ssh.selection_passed:
        blockers.extend(ssh.errors or ["existing_ssh_key_selection_required"])
    if not ssh.selected_ssh_key_name_for_payload:
        blockers.append("raw_existing_ssh_key_name_missing_from_private_artifact")
    if ssh.raw_public_key_material_present:
        blockers.append("raw_public_key_material_present")
    if planned_runtime_minutes > 30:
        blockers.append("planned_runtime_exceeds_30_minutes")
    if not _default_private_key_reference_available(ssh.selected_ssh_key_name_for_payload):
        blockers.append("approved_default_private_key_reference_missing")

    live_item = _select_live_item(
        discovery,
        price_snapshot,
        preferred_metadata_plan=preferred_metadata_plan,
    )
    if live_item is None:
        blockers.append("no_valid_m054b_live_candidate")
        shape = None
        region = None
        source = None
    else:
        shape = live_item.name or live_item.instance_type_id
        region = (
            preferred_metadata_plan.selected_region
            if preferred_metadata_plan is not None
            and preferred_metadata_plan.selected_region in live_item.regions
            else (live_item.regions[0] if live_item.regions else None)
        )
        source = (
            "m051_metadata_success_candidate_fresh_live_validated"
            if preferred_metadata_plan is not None
            and preferred_metadata_plan.selected_candidate == shape
            else "fresh_live_read_only_instance_types"
        )
        if not region:
            blockers.append("selected_candidate_region_missing")

    record = _find_price_record(price_snapshot, shape)
    price_per_hour = (
        record.price_per_instance_hour
        if record is not None
        else (live_item.price_per_hour if live_item is not None else None)
    )
    if shape is not None and price_per_hour is None:
        blockers.append("selected_candidate_price_missing")
    estimated = _estimate(price_per_hour, planned_runtime_minutes)
    buffered = None if estimated is None else round(estimated * safety_buffer_multiplier, 8)
    if buffered is not None and buffered >= max_budget:
        blockers.append("buffered_estimated_cost_not_below_max_budget")

    return LambdaSSHConnectivityM054BPlan(
        plan_status="plan_passed" if not blockers else "blocked",
        selected_candidate=shape,
        selected_region=region,
        selected_candidate_source=source,
        selected_ssh_key_hash=ssh.selected_ssh_key_name_redacted_or_hash,
        private_key_reference_available_for_probe=(
            _default_private_key_reference_available(ssh.selected_ssh_key_name_for_payload)
        ),
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


def m054b_plan_hash(plan: LambdaSSHConnectivityM054BPlan) -> str:
    material = {
        "selected_candidate": plan.selected_candidate,
        "selected_region": plan.selected_region,
        "selected_ssh_key_hash": plan.selected_ssh_key_hash,
        "ssh_connectivity_only": plan.ssh_connectivity_only,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _select_live_item(
    discovery: LambdaLiveDiscoveryReport,
    price_snapshot: PriceSnapshot,
    *,
    preferred_metadata_plan: LambdaM051MetadataBootstrapPlan | None,
):
    if preferred_metadata_plan is not None and preferred_metadata_plan.selected_candidate:
        preferred = next(
            (
                item
                for item in discovery.instance_types
                if item.name == preferred_metadata_plan.selected_candidate
                or item.instance_type_id == preferred_metadata_plan.selected_candidate
            ),
            None,
        )
        if preferred is not None:
            return preferred
    return min(
        discovery.instance_types,
        key=lambda item: (
            _price_for_item(
                item.name or item.instance_type_id,
                item.price_per_hour,
                price_snapshot,
            )
            or float("inf"),
            item.gpus or 999,
            item.name or item.instance_type_id,
        ),
        default=None,
    )


def _price_for_item(
    shape: str,
    live_price: float | None,
    price_snapshot: PriceSnapshot,
) -> float | None:
    record = _find_price_record(price_snapshot, shape)
    if record is not None:
        return record.price_per_instance_hour
    return live_price


def _find_price_record(
    price_snapshot: PriceSnapshot,
    shape: str | None,
) -> SnapshotPriceRecord | None:
    if shape is None:
        return None
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


def _default_private_key_reference_available(selected_key_name: str | None) -> bool:
    return resolve_default_private_key_path(selected_key_name) is not None


def resolve_default_private_key_path(selected_key_name: str | None) -> Path | None:
    ssh_dir = Path.home() / ".ssh"
    selected = ssh_dir / selected_key_name if selected_key_name else None
    if selected is not None and selected.is_file():
        return selected
    defaults = [path for path in [ssh_dir / "id_ed25519", ssh_dir / "id_rsa"] if path.is_file()]
    return defaults[0] if len(defaults) == 1 else None


def load_lambda_ssh_connectivity_m054b_plan(
    path: str | Path,
) -> LambdaSSHConnectivityM054BPlan:
    return LambdaSSHConnectivityM054BPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_m054b_plan(
    path: str | Path,
    report: LambdaSSHConnectivityM054BPlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
