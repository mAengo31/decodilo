import json
from datetime import UTC, datetime

from decodilo.lambda_cloud.api_models import LambdaInstanceType
from decodilo.lambda_cloud.launch_plan import build_lambda_launch_plan, write_lambda_launch_plan
from decodilo.lambda_cloud.launch_shape_resolution import (
    LambdaLaunchShapeResolutionReport,
    write_lambda_launch_shape_resolution_report,
)
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.price_reconciliation import reconcile_lambda_price_from_paths
from decodilo.pricing.snapshots import (
    PriceSnapshot,
    PriceSourceType,
    SnapshotPriceRecord,
    write_price_snapshot,
)


def _fresh_price_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_inputs(tmp_path, *, records: list[SnapshotPriceRecord], sample: bool = False):
    discovery = LambdaLiveDiscoveryReport(
        live_api_used=True,
        instance_types=[
            LambdaInstanceType(
                instance_type_id="gpu_8x_h100_sxm",
                name="8x H100 SXM",
                gpu_type="H100 SXM",
                gpus=8,
                regions=["us-west-1"],
            )
        ],
    )
    discovery_path = tmp_path / "discovery.json"
    write_lambda_live_discovery_report(discovery_path, discovery)
    snapshot = PriceSnapshot(
        snapshot_id="snap",
        provider="lambda",
        captured_at_utc=_fresh_price_timestamp(),
        source_type=PriceSourceType.MANUAL_JSON,
        source_sha256="0" * 64,
        records=records,
        is_sample_data=sample,
    )
    snapshot_path = tmp_path / "prices.json"
    write_price_snapshot(snapshot_path, snapshot)
    plan = build_lambda_launch_plan(
        run_id="run",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=0.5,
        max_run_budget=50,
    )
    plan_path = tmp_path / "plan.json"
    write_lambda_launch_plan(plan_path, plan)
    return discovery_path, snapshot_path, plan_path


def _record(record_id: str = "price-0") -> SnapshotPriceRecord:
    return SnapshotPriceRecord(
        provider="lambda",
        instance_type="gpu_8x_h100_sxm",
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        region="sample-offline",
        price_per_gpu_hour=2.5,
        price_per_instance_hour=20.0,
        captured_at_utc=_fresh_price_timestamp(),
        record_id=record_id,
    )


def test_lambda_price_reconciliation_computes_budget_arithmetic(tmp_path) -> None:
    discovery, snapshot, plan = _write_inputs(tmp_path, records=[_record()])

    report = reconcile_lambda_price_from_paths(
        discovery_report=discovery,
        price_snapshot=snapshot,
        launch_plan=plan,
        gpu_type="H100 SXM",
        credits=100,
        planned_hours=0.5,
        max_run_budget=50,
        safety_buffer_percentage=15,
    )

    assert report.base_estimated_cost == 10.0
    assert report.safety_buffer_adjusted_cost == 11.5
    assert report.projected_remaining_credits == 88.5
    assert report.price_reconciliation_passed is True
    assert json.loads(report.to_json())["launch_allowed"] is False


def test_lambda_price_reconciliation_fails_missing_and_ambiguous_price(tmp_path) -> None:
    discovery, snapshot, plan = _write_inputs(tmp_path, records=[])
    missing = reconcile_lambda_price_from_paths(
        discovery_report=discovery,
        price_snapshot=snapshot,
        launch_plan=plan,
        gpu_type="H100 SXM",
        credits=100,
        planned_hours=0.5,
        max_run_budget=50,
    )
    discovery, snapshot, plan = _write_inputs(
        tmp_path / "amb",
        records=[_record("a"), _record("b")],
    )
    ambiguous = reconcile_lambda_price_from_paths(
        discovery_report=discovery,
        price_snapshot=snapshot,
        launch_plan=plan,
        gpu_type="H100 SXM",
        credits=100,
        planned_hours=0.5,
        max_run_budget=50,
    )

    assert missing.price_reconciliation_passed is False
    assert "missing_price" in missing.price_risks
    assert ambiguous.price_reconciliation_passed is False
    assert "ambiguous_price" in ambiguous.price_risks


def test_lambda_price_reconciliation_sample_price_policy(tmp_path) -> None:
    discovery, snapshot, plan = _write_inputs(tmp_path, records=[_record()], sample=True)

    blocked = reconcile_lambda_price_from_paths(
        discovery_report=discovery,
        price_snapshot=snapshot,
        launch_plan=plan,
        gpu_type="H100 SXM",
        credits=100,
        planned_hours=0.5,
        max_run_budget=50,
    )
    allowed = reconcile_lambda_price_from_paths(
        discovery_report=discovery,
        price_snapshot=snapshot,
        launch_plan=plan,
        gpu_type="H100 SXM",
        credits=100,
        planned_hours=0.5,
        max_run_budget=50,
        allow_sample_prices=True,
    )

    assert blocked.price_reconciliation_passed is False
    assert "sample_price" in blocked.price_risks
    assert allowed.price_reconciliation_passed is True
    assert allowed.warnings


def test_lambda_price_reconciliation_uses_resolved_shape_evidence(tmp_path) -> None:
    discovery = LambdaLiveDiscoveryReport(live_api_used=True, instance_types=[])
    discovery_path = tmp_path / "discovery.json"
    write_lambda_live_discovery_report(discovery_path, discovery)
    snapshot = PriceSnapshot(
        snapshot_id="snap",
        provider="lambda",
        captured_at_utc=_fresh_price_timestamp(),
        source_type=PriceSourceType.MANUAL_HTML,
        source_url="https://lambda.ai/instances",
        source_sha256="0" * 64,
        records=[
            SnapshotPriceRecord(
                provider="lambda",
                instance_type="gpu_8x_h100_sxm",
                gpu_type="H100 SXM",
                gpus_per_instance=8,
                price_per_gpu_hour=3.99,
                price_per_instance_hour=31.92,
                captured_at_utc=_fresh_price_timestamp(),
                record_id="lambda:gpu_8x_h100_sxm:0",
            )
        ],
    )
    snapshot_path = tmp_path / "prices.json"
    write_price_snapshot(snapshot_path, snapshot)
    plan = build_lambda_launch_plan(
        run_id="run",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=0.5,
        max_run_budget=50,
    )
    plan_path = tmp_path / "plan.json"
    write_lambda_launch_plan(plan_path, plan)
    resolution = LambdaLaunchShapeResolutionReport(
        planned_gpu_type="H100 SXM",
        planned_gpus_per_instance=8,
        planned_instance_type_or_shape="gpu_8x_h100_sxm",
        matched_product_catalog_record={"instance_type": "gpu_8x_h100_sxm"},
        matched_price_record={
            "record_id": "lambda:gpu_8x_h100_sxm:0",
            "instance_type": "gpu_8x_h100_sxm",
            "price_per_gpu_hour": 3.99,
            "price_per_instance_hour": 31.92,
        },
        live_availability_status="endpoint_inconclusive",
        shape_resolution_status="resolved",
        first_launch_allowed_by_shape_evidence=True,
        warnings=["live availability remains unknown until launch attempt"],
    )
    resolution_path = tmp_path / "resolution.json"
    write_lambda_launch_shape_resolution_report(resolution_path, resolution)

    report = reconcile_lambda_price_from_paths(
        discovery_report=discovery_path,
        price_snapshot=snapshot_path,
        launch_plan=plan_path,
        gpu_type="H100 SXM",
        credits=100,
        planned_hours=0.5,
        max_run_budget=50,
        safety_buffer_percentage=15,
        shape_resolution=resolution_path,
    )

    assert report.price_reconciliation_passed is True
    assert report.shape_match.match_status == "matched"
    assert report.base_estimated_cost == 15.96
    assert "missing_price" not in report.price_risks
