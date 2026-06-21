"""Metadata-only M051 Lambda bootstrap launch plan."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lifecycle_smoke_closeout import (
    load_lambda_lifecycle_smoke_closeout,
)
from decodilo.lambda_cloud.lifecycle_smoke_success_record import (
    load_lambda_lifecycle_smoke_success_record,
)
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.m051_bootstrap_authorization import (
    load_lambda_m051_bootstrap_authorization,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot


class LambdaM051MetadataBootstrapPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    plan_passed: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    selected_candidate_source: str | None = None
    quantity: int = 1
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    selected_ssh_key_hash: str | None = None
    metadata_only: bool = True
    ssh_key_attached_for_payload_only: bool = True
    ssh_used: bool = False
    remote_commands_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    filesystem_attached: bool = False
    strand_payload_compatible: bool = True
    live_candidate_validated: bool = False
    lifecycle_success_candidate_used: bool = False
    price_per_instance_hour: float | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    max_budget: float = 50.0
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM051MetadataBootstrapPlan:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.ssh_used
            or self.remote_commands_allowed
            or self.package_install_allowed
            or self.training_allowed
            or self.setup_scripts_allowed
            or self.cloud_init_allowed
            or self.filesystem_attached
        ):
            raise ValueError("M051 metadata plan cannot enable launch or remote work")
        if self.plan_passed and self.blockers:
            raise ValueError("M051 metadata plan cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_metadata_bootstrap_plan_from_paths(
    *,
    discovery_report: str | Path,
    bootstrap_authorization: str | Path,
    ssh_key_selection: str | Path,
    price_snapshot: str | Path,
    lifecycle_success_record: str | Path | None = None,
    lifecycle_closeout: str | Path | None = None,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaM051MetadataBootstrapPlan:
    return build_lambda_m051_metadata_bootstrap_plan(
        discovery=load_lambda_live_discovery_report(discovery_report),
        authorization_path=bootstrap_authorization,
        ssh_key_selection_path=ssh_key_selection,
        price_snapshot=load_price_snapshot(price_snapshot),
        lifecycle_success_record_path=lifecycle_success_record,
        lifecycle_closeout_path=lifecycle_closeout,
        max_budget=max_budget,
        planned_runtime_minutes=planned_runtime_minutes,
        safety_buffer_multiplier=safety_buffer_multiplier,
    )


def build_lambda_m051_metadata_bootstrap_plan(
    *,
    discovery: LambdaLiveDiscoveryReport,
    authorization_path: str | Path,
    ssh_key_selection_path: str | Path,
    price_snapshot: PriceSnapshot,
    lifecycle_success_record_path: str | Path | None = None,
    lifecycle_closeout_path: str | Path | None = None,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaM051MetadataBootstrapPlan:
    auth = load_lambda_m051_bootstrap_authorization(authorization_path)
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection_path)
    blockers: list[str] = []
    warnings = [
        "metadata-only bootstrap plan is review evidence until m029 run arms it",
        "SSH key attachment does not approve SSH use",
    ]

    if auth.authorization_status != (
        "authorized_for_future_m051_metadata_only_bootstrap_review"
    ):
        blockers.append("m051_metadata_authorization_not_ready")
    if auth.selected_bootstrap_mode != "lifecycle_plus_metadata_only":
        blockers.append("bootstrap_mode_must_be_metadata_only")
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
        blockers.append("sample_price_snapshot_cannot_authorize_metadata_bootstrap")
    if not ssh.selection_passed:
        blockers.extend(ssh.errors or ["existing_ssh_key_selection_required"])
    if ssh.raw_public_key_material_present:
        blockers.append("raw_public_key_material_present")
    if not ssh.selected_ssh_key_name_for_payload:
        blockers.append("raw_existing_ssh_key_name_missing_from_private_artifact")
    if planned_runtime_minutes > 30:
        blockers.append("planned_runtime_exceeds_30_minutes")

    target_shape, target_region, lifecycle_used = _lifecycle_target(
        lifecycle_success_record_path,
        lifecycle_closeout_path,
        blockers,
    )
    live_item = None
    if target_shape is not None:
        live_item = next(
            (
                item
                for item in discovery.instance_types
                if item.name == target_shape or item.instance_type_id == target_shape
            ),
            None,
        )
        if live_item is None:
            blockers.append("lifecycle_success_candidate_not_present_in_fresh_live_catalog")
        elif target_region and live_item.regions and target_region not in live_item.regions:
            blockers.append("lifecycle_success_region_not_present_in_fresh_live_catalog")
    elif discovery.instance_types:
        live_item = _cheapest_live_item(discovery, price_snapshot)
        target_shape = None if live_item is None else (live_item.name or live_item.instance_type_id)
        target_region = (
            None
            if live_item is None
            else (live_item.regions[0] if live_item.regions else None)
        )
        warnings.append(
            "selected cheapest fresh live candidate because lifecycle target was absent"
        )
    else:
        blockers.append("no_valid_metadata_bootstrap_candidate")

    if live_item is not None and not target_region:
        target_region = live_item.regions[0] if live_item.regions else None
    if live_item is not None and not target_region:
        blockers.append("selected_candidate_region_missing")

    record = _find_price_record(price_snapshot, target_shape)
    price_per_hour = (
        None
        if record is None
        else record.price_per_instance_hour
    )
    if price_per_hour is None and live_item is not None:
        price_per_hour = live_item.price_per_hour
    if target_shape is not None and price_per_hour is None:
        blockers.append("selected_candidate_price_missing")
    estimated = _estimate(price_per_hour, planned_runtime_minutes)
    buffered = None if estimated is None else round(estimated * safety_buffer_multiplier, 8)
    if buffered is not None and buffered >= max_budget:
        blockers.append("buffered_estimated_cost_not_below_max_budget")

    return LambdaM051MetadataBootstrapPlan(
        plan_passed=not blockers,
        selected_candidate=target_shape if not blockers else target_shape,
        selected_region=target_region,
        selected_candidate_source=(
            "lifecycle_success_fresh_live_catalog_validated"
            if lifecycle_used
            else "fresh_live_read_only_instance_types"
        )
        if target_shape
        else None,
        gpu_type=(
            record.gpu_type
            if record is not None
            else (live_item.gpu_type if live_item else None)
        ),
        gpus_per_instance=(
            record.gpus_per_instance
            if record is not None
            else (live_item.gpus or None if live_item else None)
        ),
        selected_ssh_key_hash=ssh.selected_ssh_key_name_redacted_or_hash,
        live_candidate_validated=live_item is not None and not blockers,
        lifecycle_success_candidate_used=lifecycle_used,
        price_per_instance_hour=price_per_hour,
        estimated_30min_cost=estimated,
        buffered_estimated_30min_cost=buffered,
        max_budget=max_budget,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def _lifecycle_target(
    lifecycle_success_record_path: str | Path | None,
    lifecycle_closeout_path: str | Path | None,
    blockers: list[str],
) -> tuple[str | None, str | None, bool]:
    if lifecycle_success_record_path is None and lifecycle_closeout_path is None:
        return None, None, False
    if lifecycle_success_record_path is None or lifecycle_closeout_path is None:
        blockers.append("both_lifecycle_success_record_and_closeout_required")
        return None, None, False
    success = load_lambda_lifecycle_smoke_success_record(lifecycle_success_record_path)
    closeout = load_lambda_lifecycle_smoke_closeout(lifecycle_closeout_path)
    if success.status != "lifecycle_smoke_success":
        blockers.append("lifecycle_success_record_not_success")
    if not closeout.closeout_succeeded:
        blockers.append("lifecycle_closeout_not_succeeded")
    return success.selected_candidate or success.instance_type_name, success.selected_region, True


def _cheapest_live_item(
    discovery: LambdaLiveDiscoveryReport,
    price_snapshot: PriceSnapshot,
):
    return min(
        discovery.instance_types,
        key=lambda item: (
            _price_for_item(item.name or item.instance_type_id, item.price_per_hour, price_snapshot)
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


def metadata_bootstrap_plan_hash(plan: LambdaM051MetadataBootstrapPlan) -> str:
    material = {
        "selected_candidate": plan.selected_candidate,
        "selected_region": plan.selected_region,
        "selected_ssh_key_hash": plan.selected_ssh_key_hash,
        "metadata_only": plan.metadata_only,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_lambda_m051_metadata_bootstrap_plan(
    path: str | Path,
) -> LambdaM051MetadataBootstrapPlan:
    return LambdaM051MetadataBootstrapPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_metadata_bootstrap_plan(
    path: str | Path,
    report: LambdaM051MetadataBootstrapPlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
