from __future__ import annotations

from pathlib import Path

from lambda_m037r_helpers import controls, discovery, ssh_selection
from lambda_m040_helpers import write_m040_inputs
from lambda_m044_helpers import m044_price_snapshot

from decodilo.lambda_cloud.capacity_aware_retry_policy import (
    build_lambda_capacity_aware_retry_policy_from_path,
    write_lambda_capacity_aware_retry_policy,
)
from decodilo.lambda_cloud.capacity_history import (
    build_lambda_capacity_history_from_paths,
    write_lambda_capacity_history,
)
from decodilo.lambda_cloud.capacity_history_aware_selector import (
    build_lambda_capacity_history_aware_selector_from_paths,
    write_lambda_capacity_history_aware_selector,
)
from decodilo.lambda_cloud.capacity_history_selector_authorization import (
    build_lambda_capacity_history_selector_authorization_from_paths,
    write_lambda_capacity_history_selector_authorization,
)
from decodilo.lambda_cloud.capacity_history_selector_command_preview import (
    build_lambda_capacity_history_selector_command_preview_from_paths,
    write_lambda_capacity_history_selector_command_preview,
)
from decodilo.lambda_cloud.capacity_history_selector_gate_check import (
    build_lambda_capacity_history_selector_gate_check_from_paths,
    write_lambda_capacity_history_selector_gate_check,
)
from decodilo.lambda_cloud.live_discovery_report import write_lambda_live_discovery_report
from decodilo.lambda_cloud.m044h_report import (
    build_lambda_m044h_report_from_paths,
    write_lambda_m044h_report,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    write_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    write_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import (
    PriceSnapshot,
    PriceSourceType,
    SnapshotPriceRecord,
    write_price_snapshot,
)


def write_m044h_inputs(
    tmp_path: Path,
    *,
    prices: PriceSnapshot | None = None,
    live_failed_shape: bool = False,
    missing_ssh: bool = False,
) -> dict[str, Path]:
    base = write_m040_inputs(tmp_path)
    paths = {
        **base,
        "history": tmp_path / "capacity-history.json",
        "retry": tmp_path / "retry-policy.json",
        "prices": tmp_path / "prices.json",
        "discovery": tmp_path / "discovery.json",
        "ssh": tmp_path / "ssh.json",
        "controls": tmp_path / "controls.json",
        "selector_m044h": tmp_path / "capacity-aware-selector.json",
        "authorization_m044h": tmp_path / "capacity-aware-authorization.json",
        "gate_m044h": tmp_path / "capacity-aware-gate.json",
        "preview_m044h": tmp_path / "capacity-aware-preview.json",
        "m044h": tmp_path / "m044h.json",
    }
    history = build_lambda_capacity_history_from_paths(
        latest_closeout=base["closeout"],
        previous_closeout=base["closeout"],
    )
    write_lambda_capacity_history(paths["history"], history)
    retry = build_lambda_capacity_aware_retry_policy_from_path(history=paths["history"])
    write_lambda_capacity_aware_retry_policy(paths["retry"], retry)
    write_price_snapshot(paths["prices"], prices or m044_price_snapshot())
    write_lambda_live_discovery_report(
        paths["discovery"],
        discovery(include_shape=live_failed_shape),
    )
    write_lambda_existing_ssh_key_selection(
        paths["ssh"],
        ssh_selection(ssh_key_names=() if missing_ssh else ("existing-key",)),
    )
    write_lambda_strand_response_loss_control_check(paths["controls"], controls())
    selector = build_lambda_capacity_history_aware_selector_from_paths(
        capacity_history=paths["history"],
        capacity_retry_policy=paths["retry"],
        price_snapshot=paths["prices"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
        discovery_report=paths["discovery"],
    )
    write_lambda_capacity_history_aware_selector(paths["selector_m044h"], selector)
    auth = build_lambda_capacity_history_selector_authorization_from_paths(
        selector_output=paths["selector_m044h"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )
    write_lambda_capacity_history_selector_authorization(paths["authorization_m044h"], auth)
    gate = build_lambda_capacity_history_selector_gate_check_from_paths(
        authorization=paths["authorization_m044h"],
        selector_output=paths["selector_m044h"],
    )
    write_lambda_capacity_history_selector_gate_check(paths["gate_m044h"], gate)
    preview = build_lambda_capacity_history_selector_command_preview_from_paths(
        authorization=paths["authorization_m044h"],
        gate_check=paths["gate_m044h"],
    )
    write_lambda_capacity_history_selector_command_preview(paths["preview_m044h"], preview)
    report = build_lambda_m044h_report_from_paths(
        selector_output=paths["selector_m044h"],
        authorization=paths["authorization_m044h"],
        gate_check=paths["gate_m044h"],
        command_preview=paths["preview_m044h"],
    )
    write_lambda_m044h_report(paths["m044h"], report)
    return paths


def only_failed_shape_price_snapshot():
    return PriceSnapshot(
        snapshot_id="lambda-test-only-failed-shape",
        provider="lambda",
        captured_at_utc="2026-06-19T00:00:00Z",
        source_url="https://lambda.ai/instances",
        source_type=PriceSourceType.MANUAL_JSON,
        source_sha256="c" * 64,
        records=[
            SnapshotPriceRecord(
                provider="lambda",
                product_family="on_demand_instance",
                instance_type="gpu_1x_h100_pcie",
                gpu_type="H100 PCIe",
                gpus_per_instance=1,
                price_per_gpu_hour=3.29,
                price_per_instance_hour=3.29,
                captured_at_utc="2026-06-19T00:00:00Z",
                record_id="lambda:gpu_1x_h100_pcie:only",
            )
        ],
        notes="only failed capacity shape",
        is_sample_data=False,
    )
