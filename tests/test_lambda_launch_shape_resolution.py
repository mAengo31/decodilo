from decodilo.lambda_cloud.availability_evidence import LambdaAvailabilityEvidence
from decodilo.lambda_cloud.launch_shape_resolution import (
    LambdaPlannedLaunchShape,
    resolve_lambda_launch_shape,
)
from decodilo.lambda_cloud.product_catalog_evidence import LambdaProductCatalogRecord
from decodilo.pricing.snapshots import PriceSnapshot, PriceSourceType, SnapshotPriceRecord


def _catalog_record():
    return LambdaProductCatalogRecord(
        instance_type="gpu_8x_h100_sxm",
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        gpu_memory_gb=80,
        price_per_gpu_hour=3.99,
        price_per_instance_hour=31.92,
        source_url="https://lambda.ai/instances",
        captured_at_utc="2026-06-18T00:00:00Z",
        source_hash="b" * 64,
    )


def _snapshot(*, sample: bool = False):
    return PriceSnapshot(
        snapshot_id="snap",
        provider="lambda",
        captured_at_utc="2026-06-18T00:00:00Z",
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
                captured_at_utc="2026-06-18T00:00:00Z",
                record_id="lambda:gpu_8x_h100_sxm:0",
            )
        ],
        is_sample_data=sample,
    )


def _planned():
    return LambdaPlannedLaunchShape(
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        instance_type_or_shape="gpu_8x_h100_sxm",
        region="us-west-1",
    )


def test_catalog_and_non_sample_price_resolve_despite_inconclusive_api():
    report = resolve_lambda_launch_shape(
        planned_shape=_planned(),
        catalog_records=[_catalog_record()],
        price_snapshot=_snapshot(),
        availability=LambdaAvailabilityEvidence(status="endpoint_inconclusive"),
    )

    assert report.shape_resolution_status == "resolved"
    assert report.first_launch_allowed_by_shape_evidence is True
    assert "live availability remains unknown until launch attempt" in report.warnings
    assert report.launch_allowed is False


def test_sample_price_blocks_shape_resolution():
    report = resolve_lambda_launch_shape(
        planned_shape=_planned(),
        catalog_records=[_catalog_record()],
        price_snapshot=_snapshot(sample=True),
        availability=LambdaAvailabilityEvidence(status="endpoint_inconclusive"),
    )

    assert report.shape_resolution_status == "unresolved_missing_price"
    assert report.first_launch_allowed_by_shape_evidence is False


def test_missing_catalog_blocks_shape_resolution():
    report = resolve_lambda_launch_shape(
        planned_shape=_planned(),
        catalog_records=[],
        price_snapshot=_snapshot(),
        availability=LambdaAvailabilityEvidence(status="endpoint_inconclusive"),
    )

    assert report.shape_resolution_status == "unresolved_missing_product_catalog"
