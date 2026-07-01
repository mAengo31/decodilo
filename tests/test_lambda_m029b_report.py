from datetime import UTC, datetime

from decodilo.lambda_cloud.launch_shape_resolution import (
    LambdaLaunchShapeResolutionReport,
)
from decodilo.lambda_cloud.m029b_report import build_lambda_m029b_report
from decodilo.pricing.snapshots import (
    PriceSnapshot,
    PriceSourceType,
    SnapshotPriceRecord,
    write_price_snapshot,
)


def _fresh_price_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_snapshot(tmp_path, *, sample=False):
    path = tmp_path / "prices.json"
    write_price_snapshot(
        path,
        PriceSnapshot(
            snapshot_id="snap",
            provider="lambda",
            captured_at_utc=_fresh_price_timestamp(),
            source_url="https://lambda.ai/instances",
            source_type=PriceSourceType.MANUAL_HTML,
            source_sha256="a" * 64,
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
            is_sample_data=sample,
        ),
    )
    return path


def test_m029b_report_keeps_launch_disabled_with_resolved_shape(tmp_path):
    report = build_lambda_m029b_report(
        shape_resolution=LambdaLaunchShapeResolutionReport(
            planned_gpu_type="H100 SXM",
            planned_gpus_per_instance=8,
            planned_instance_type_or_shape="gpu_8x_h100_sxm",
            matched_product_catalog_record={"instance_type": "gpu_8x_h100_sxm"},
            matched_price_record={"record_id": "lambda:gpu_8x_h100_sxm:0"},
            live_availability_status="endpoint_inconclusive",
            shape_resolution_status="resolved",
            first_launch_allowed_by_shape_evidence=True,
        ),
        price_snapshot=_write_snapshot(tmp_path),
    )

    assert report.shape_gate_passed is True
    assert report.price_gate_passed is True
    assert report.launch_allowed is False
    assert report.billable_action_performed is False


def test_m029b_report_blocks_sample_price(tmp_path):
    report = build_lambda_m029b_report(
        shape_resolution=LambdaLaunchShapeResolutionReport(
            planned_gpu_type="H100 SXM",
            planned_gpus_per_instance=8,
            planned_instance_type_or_shape="gpu_8x_h100_sxm",
            live_availability_status="endpoint_inconclusive",
            shape_resolution_status="unresolved_missing_price",
            first_launch_allowed_by_shape_evidence=False,
            errors=["sample price snapshot cannot support first launch"],
        ),
        price_snapshot=_write_snapshot(tmp_path, sample=True),
    )

    assert report.shape_gate_passed is False
    assert report.price_gate_passed is False
    assert report.launch_allowed is False
