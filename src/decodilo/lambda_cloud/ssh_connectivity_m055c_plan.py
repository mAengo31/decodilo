"""M055C SSH-connectivity diagnostic retry plan."""

from __future__ import annotations

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
from decodilo.lambda_cloud.ssh_failure_stderr_capture import (
    load_lambda_ssh_stderr_capture_policy,
)
from decodilo.lambda_cloud.ssh_host_key_policy import load_lambda_ssh_host_key_policy
from decodilo.lambda_cloud.ssh_identity_policy import load_lambda_ssh_identity_policy
from decodilo.lambda_cloud.ssh_private_key_file_policy import (
    load_lambda_ssh_private_key_file_policy,
)
from decodilo.lambda_cloud.ssh_username_policy import load_lambda_ssh_username_policy
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot

LambdaSSHConnectivityM055CPlanStatus = Literal["plan_passed", "blocked"]


class LambdaSSHConnectivityM055CPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M055C"
    plan_status: LambdaSSHConnectivityM055CPlanStatus
    selected_candidate: str | None = None
    selected_region: str | None = None
    selected_candidate_source: str | None = None
    quantity: int = 1
    selected_ssh_key_hash: str | None = None
    ssh_username: str = "ubuntu"
    identities_only: bool = True
    isolated_known_hosts: bool = True
    strict_host_key_checking_policy: str = "accept-new"
    stderr_capture_enabled: bool = True
    max_ssh_attempts: int = 1
    max_launch_attempts: int = 1
    no_auto_retry: bool = True
    no_remote_command: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_training: bool = True
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    price_per_instance_hour: float | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    response_capture_active: bool = True
    status_before_parse: bool = True
    effective_launch_timeout_seconds: float = 30.0
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHConnectivityM055CPlan:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.identities_only
            or not self.isolated_known_hosts
            or not self.stderr_capture_enabled
            or not self.no_auto_retry
            or not self.no_remote_command
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_package_install
            or not self.no_training
            or self.max_ssh_attempts != 1
            or self.max_launch_attempts != 1
        ):
            raise ValueError("M055C plan violates one-shot diagnostic constraints")
        if self.plan_status == "plan_passed" and self.blockers:
            raise ValueError("passing M055C plan cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_connectivity_m055c_plan_from_paths(
    *,
    discovery_report: str | Path,
    username_policy: str | Path,
    host_key_policy: str | Path,
    identity_policy: str | Path,
    private_key_file_policy: str | Path,
    stderr_capture_policy: str | Path,
    ssh_key_selection: str | Path,
    price_snapshot: str | Path,
    preferred_metadata_plan: str | Path | None = Path(
        "/tmp/decodilo-lambda-m051-metadata-bootstrap-plan.json"
    ),
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaSSHConnectivityM055CPlan:
    preferred = (
        load_lambda_m051_metadata_bootstrap_plan(preferred_metadata_plan)
        if preferred_metadata_plan is not None and Path(preferred_metadata_plan).exists()
        else None
    )
    return build_lambda_ssh_connectivity_m055c_plan(
        discovery=load_lambda_live_discovery_report(discovery_report),
        username_policy_path=username_policy,
        host_key_policy_path=host_key_policy,
        identity_policy_path=identity_policy,
        private_key_file_policy_path=private_key_file_policy,
        stderr_capture_policy_path=stderr_capture_policy,
        ssh_key_selection_path=ssh_key_selection,
        price_snapshot=load_price_snapshot(price_snapshot),
        preferred_metadata_plan=preferred,
        max_budget=max_budget,
        planned_runtime_minutes=planned_runtime_minutes,
        safety_buffer_multiplier=safety_buffer_multiplier,
    )


def build_lambda_ssh_connectivity_m055c_plan(
    *,
    discovery: LambdaLiveDiscoveryReport,
    username_policy_path: str | Path,
    host_key_policy_path: str | Path,
    identity_policy_path: str | Path,
    private_key_file_policy_path: str | Path,
    stderr_capture_policy_path: str | Path,
    ssh_key_selection_path: str | Path,
    price_snapshot: PriceSnapshot,
    preferred_metadata_plan: LambdaM051MetadataBootstrapPlan | None = None,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaSSHConnectivityM055CPlan:
    username = load_lambda_ssh_username_policy(username_policy_path)
    host_key = load_lambda_ssh_host_key_policy(host_key_policy_path)
    identity = load_lambda_ssh_identity_policy(identity_policy_path)
    key_file = load_lambda_ssh_private_key_file_policy(private_key_file_policy_path)
    stderr_policy = load_lambda_ssh_stderr_capture_policy(stderr_capture_policy_path)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection_path)
    blockers: list[str] = []
    warnings = [
        "M055C plan is non-executable until the one-shot reviewer bridge is used",
        "bounded redacted stderr capture is required for SSH failure classification",
    ]
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
    if price_snapshot.is_sample_data:
        blockers.append("sample_price_snapshot_cannot_authorize_m055c")
    if username.username_policy_status != "policy_defined":
        blockers.extend(username.blockers or ["username_policy_not_defined"])
    if username.selected_username != "ubuntu":
        blockers.append("m055c_requires_ubuntu_username")
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

    live_item = _select_live_item(
        discovery,
        price_snapshot,
        preferred_metadata_plan=preferred_metadata_plan,
    )
    if live_item is None:
        blockers.append("no_valid_m055c_live_candidate")
        shape = None
        region = None
        source = None
    else:
        shape = live_item.name or live_item.instance_type_id
        region = _select_region(live_item.regions, preferred_metadata_plan, discovery)
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

    return LambdaSSHConnectivityM055CPlan(
        plan_status="plan_passed" if not blockers else "blocked",
        selected_candidate=shape,
        selected_region=region,
        selected_candidate_source=source,
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


def _select_region(
    regions: list[str],
    preferred_metadata_plan: LambdaM051MetadataBootstrapPlan | None,
    discovery: LambdaLiveDiscoveryReport,
) -> str | None:
    if (
        preferred_metadata_plan is not None
        and (
            preferred_metadata_plan.selected_region in regions
            or (
                not regions
                and _discovery_has_region(
                    discovery,
                    preferred_metadata_plan.selected_region,
                )
            )
        )
    ):
        return preferred_metadata_plan.selected_region
    return regions[0] if regions else None


def _discovery_has_region(
    discovery: LambdaLiveDiscoveryReport,
    region_name: str | None,
) -> bool:
    if not region_name:
        return False
    return any(
        region.name == region_name or region.region_id == region_name
        for region in discovery.regions
    )


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


def load_lambda_ssh_connectivity_m055c_plan(
    path: str | Path,
) -> LambdaSSHConnectivityM055CPlan:
    return LambdaSSHConnectivityM055CPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_m055c_plan(
    path: str | Path,
    report: LambdaSSHConnectivityM055CPlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
