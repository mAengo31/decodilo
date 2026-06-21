from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.lifecycle_smoke_closeout import (
    build_lambda_lifecycle_smoke_closeout_from_paths,
    write_lambda_lifecycle_smoke_closeout,
)
from decodilo.lambda_cloud.lifecycle_smoke_evidence_package import (
    build_lambda_lifecycle_smoke_evidence_package_from_paths,
    write_lambda_lifecycle_smoke_evidence_package,
)
from decodilo.lambda_cloud.lifecycle_smoke_postrun_reconciliation import (
    build_lambda_lifecycle_smoke_postrun_reconciliation_from_paths,
    write_lambda_lifecycle_smoke_postrun_reconciliation,
)
from decodilo.lambda_cloud.lifecycle_smoke_success_record import (
    build_lambda_lifecycle_smoke_success_record_from_paths,
    write_lambda_lifecycle_smoke_success_record,
)
from decodilo.lambda_cloud.live_discovery_report import LambdaLiveDiscoveryReport
from decodilo.lambda_cloud.live_instance_type_parser import (
    build_lambda_live_instance_type_parser_from_path,
    write_lambda_live_instance_type_parser,
)
from decodilo.lambda_cloud.live_region_selection import (
    build_lambda_live_region_selection_from_paths,
    write_lambda_live_region_selection,
)
from decodilo.lambda_cloud.live_shape_alias_resolution import (
    build_lambda_live_shape_alias_resolution_from_paths,
    write_lambda_live_shape_alias_resolution,
)
from decodilo.lambda_cloud.live_shape_price_join import (
    build_lambda_live_shape_price_join_from_paths,
    write_lambda_live_shape_price_join,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report
from decodilo.lambda_cloud.m047_report import (
    build_lambda_m047_report_from_paths,
    write_lambda_m047_report,
)
from decodilo.lambda_cloud.read_only_audit import LambdaReadOnlyAuditEntry
from decodilo.lambda_cloud.real_launch_spend_audit import LambdaM029SpendAuditReport
from decodilo.lambda_cloud.successful_launch_strategy_update import (
    build_lambda_successful_launch_strategy_update_from_paths,
    write_lambda_successful_launch_strategy_update,
)
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, write_price_snapshot

SUCCESS_SHAPE = "gpu_8x_a100_80gb_sxm4"
STALE_SHAPE = "gpu_8x_a100_sxm_80gb"
SUCCESS_REGION = "us-midwest-1"


def live_instance_types_payload() -> dict:
    return {
        "data": {
            "gpu_1x_h100_pcie": {
                "instance_type": {
                    "name": "gpu_1x_h100_pcie",
                    "description": "1x H100 (80 GB PCIe)",
                    "gpu_description": "H100 (80 GB PCIe)",
                    "price_cents_per_hour": 329,
                },
                "regions_with_capacity_available": [{"name": "us-west-3"}],
            },
            SUCCESS_SHAPE: {
                "instance_type": {
                    "name": SUCCESS_SHAPE,
                    "description": "8x A100 (80 GB SXM4)",
                    "gpu_description": "A100 (80 GB SXM4)",
                    "price_cents_per_hour": 2232,
                },
                "regions_with_capacity_available": [
                    {"name": "us-east-1"},
                    {"name": SUCCESS_REGION},
                ],
            },
        }
    }


def list_instance_types_payload() -> dict:
    return {
        "data": [
            {
                "name": SUCCESS_SHAPE,
                "description": "8x A100 (80 GB SXM4)",
                "gpu_description": "A100 (80 GB SXM4)",
                "price_cents_per_hour": 2232,
                "regions_with_capacity_available": [{"name": SUCCESS_REGION}],
            }
        ]
    }


def write_price_snapshot_fixture(path: Path, *, sample: bool = False) -> None:
    snapshot = PriceSnapshot(
        snapshot_id="lambda-m047-fixture",
        provider="lambda",
        captured_at_utc="2026-06-20T19:18:35Z",
        source_type="manual_json",
        source_sha256="0" * 64,
        records=[
            SnapshotPriceRecord(
                provider="lambda",
                product_family="instances",
                instance_type=SUCCESS_SHAPE,
                gpu_type="A100 80GB SXM4",
                gpus_per_instance=8,
                gpu_memory_gb=80,
                price_per_gpu_hour=2.79,
                price_per_instance_hour=22.32,
                captured_at_utc="2026-06-20T19:18:35Z",
                record_id=f"lambda:{SUCCESS_SHAPE}:0",
            )
        ],
        is_sample_data=sample,
    )
    write_price_snapshot(path, snapshot)


def write_m046c_workdir(
    base: Path,
    *,
    termination_verified: bool = True,
    final_instance_count: int = 0,
    unmanaged_count: int = 0,
) -> dict[str, Path]:
    workdir = base / "workdir"
    workdir.mkdir(parents=True)
    report = LambdaM029Report(
        run_id="lambda-m046-capacity-selected-launch",
        real_lambda_api_used=True,
        launch_request_sent=True,
        launch_response_received=True,
        owned_instance_id_redacted="6af7df...984d",
        readonly_verify_running_result="running",
        termination_request_sent=True,
        termination_response_received=termination_verified,
        readonly_verify_terminated_result=(
            "terminated" if termination_verified else "running"
        ),
        termination_verified=termination_verified,
        manual_review_required=not termination_verified,
        mutating_operations=2,
        billable_action_performed=True,
        estimated_spend=0.042826,
        elapsed_seconds=6.907,
        launch_response_http_status=200,
        launch_response_content_type="application/json",
        launch_response_body_size_bytes=63,
        launch_response_classification="success_json",
        termination_response_http_status=200 if termination_verified else None,
        termination_response_content_type=(
            "application/json" if termination_verified else None
        ),
        termination_response_body_size_bytes=652 if termination_verified else None,
        termination_response_classification=(
            "success_json" if termination_verified else None
        ),
        capacity_selected_path_used=True,
        selected_shape=SUCCESS_SHAPE,
        selected_candidate=SUCCESS_SHAPE,
        selected_candidate_source="live_read_only",
        selected_region=SUCCESS_REGION,
        selected_ssh_key_hash="sha256:e8bd9b2e6fc17b09",
        strand_payload_compatible=True,
        no_auto_launch_retry=True,
        response_capture_active=True,
        old_path_fallback_blocked=True,
        m039_path_fallback_blocked=True,
    )
    (workdir / "report.json").write_text(report.to_json(), encoding="utf-8")
    (workdir / "journal.jsonl").write_text(
        json.dumps({"event": "launch"}) + "\n"
        + json.dumps({"event": "terminate"}) + "\n",
        encoding="utf-8",
    )
    (workdir / "ledger.json").write_text(
        json.dumps({"owned_instance_id_redacted": "6af7df...984d"}, indent=2) + "\n",
        encoding="utf-8",
    )
    spend = LambdaM029SpendAuditReport(
        estimated_hourly_cost=22.32,
        actual_elapsed_seconds=6.907,
        estimated_spend=0.191873,
        budget_exceeded=False,
        runtime_exceeded=False,
        billable_action_performed=True,
        launch_request_sent=True,
        terminate_request_sent=True,
        termination_verified=termination_verified,
    )
    (workdir / "spend-audit.json").write_text(spend.to_json(), encoding="utf-8")
    final_summary = base / "final-summary.json"
    final_summary.write_text(
        json.dumps({"secret_scan_findings": {}}, indent=2) + "\n",
        encoding="utf-8",
    )
    instances = [
        {"instance_id": "i-leftover", "name": "leftover", "status": "running"}
        for _ in range(final_instance_count)
    ]
    discovery = LambdaLiveDiscoveryReport(
        live_api_used=True,
        instances=instances,
        unmanaged_instances=[f"unmanaged-{i}" for i in range(unmanaged_count)],
        audit_log=[
            LambdaReadOnlyAuditEntry(
                operation="list_instances",
                method="GET",
                endpoint="/instances",
                allowed=True,
                status_code=200,
                live_api_used=True,
            )
        ],
    )
    post_discovery = base / "post-discovery.json"
    post_discovery.write_text(discovery.to_json(), encoding="utf-8")
    return {
        "workdir": workdir,
        "final_summary": final_summary,
        "post_discovery": post_discovery,
    }


def write_m047_inputs(base: Path) -> dict[str, Path]:
    paths = write_m046c_workdir(base)
    paths.update(
        {
            "success": base / "success-record.json",
            "reconciliation": base / "reconciliation.json",
            "evidence": base / "evidence-package.json",
            "closeout": base / "closeout.json",
            "raw_instance_types": base / "instance-types-raw.json",
            "parsed_instance_types": base / "instance-types-parsed.json",
            "region_selection": base / "region-selection.json",
            "alias": base / "alias.json",
            "price_snapshot": base / "price-snapshot.json",
            "price_join": base / "price-join.json",
            "strategy": base / "strategy.json",
            "m047": base / "m047.json",
        }
    )
    success = build_lambda_lifecycle_smoke_success_record_from_paths(
        workdir=paths["workdir"],
        final_summary=paths["final_summary"],
        post_discovery=paths["post_discovery"],
    )
    write_lambda_lifecycle_smoke_success_record(paths["success"], success)
    reconciliation = build_lambda_lifecycle_smoke_postrun_reconciliation_from_paths(
        workdir=paths["workdir"],
        post_discovery=paths["post_discovery"],
    )
    write_lambda_lifecycle_smoke_postrun_reconciliation(
        paths["reconciliation"],
        reconciliation,
    )
    evidence = build_lambda_lifecycle_smoke_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )
    write_lambda_lifecycle_smoke_evidence_package(paths["evidence"], evidence)
    closeout = build_lambda_lifecycle_smoke_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )
    write_lambda_lifecycle_smoke_closeout(paths["closeout"], closeout)
    paths["raw_instance_types"].write_text(
        json.dumps(live_instance_types_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    parsed = build_lambda_live_instance_type_parser_from_path(
        paths["raw_instance_types"]
    )
    write_lambda_live_instance_type_parser(paths["parsed_instance_types"], parsed)
    region = build_lambda_live_region_selection_from_paths(
        instance_types=paths["parsed_instance_types"],
        candidate=SUCCESS_SHAPE,
        prior_successful_region=SUCCESS_REGION,
    )
    write_lambda_live_region_selection(paths["region_selection"], region)
    alias = build_lambda_live_shape_alias_resolution_from_paths(
        instance_types=paths["parsed_instance_types"],
        requested_shape=STALE_SHAPE,
    )
    write_lambda_live_shape_alias_resolution(paths["alias"], alias)
    write_price_snapshot_fixture(paths["price_snapshot"])
    price = build_lambda_live_shape_price_join_from_paths(
        price_snapshot=paths["price_snapshot"],
        live_instance_type_name=SUCCESS_SHAPE,
        alias_resolution=paths["alias"],
    )
    write_lambda_live_shape_price_join(paths["price_join"], price)
    strategy = build_lambda_successful_launch_strategy_update_from_paths(
        success_record=paths["success"],
        live_region_selection=paths["region_selection"],
    )
    write_lambda_successful_launch_strategy_update(paths["strategy"], strategy)
    report = build_lambda_m047_report_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        closeout=paths["closeout"],
        live_region_selection=paths["region_selection"],
        evidence_package=paths["evidence"],
        live_parser=paths["parsed_instance_types"],
        alias_resolution=paths["alias"],
        price_join=paths["price_join"],
        strategy_update=paths["strategy"],
    )
    write_lambda_m047_report(paths["m047"], report)
    return paths
