from decodilo.lambda_cloud.non_sample_price_snapshot import (
    validate_non_sample_price_snapshot,
)
from decodilo.pricing.snapshots import PriceSnapshot, PriceSourceType, SnapshotPriceRecord


def _snapshot(*, sample: bool = False, captured: str = "2026-06-18T00:00:00Z"):
    return PriceSnapshot(
        snapshot_id="snap",
        provider="lambda",
        captured_at_utc=captured,
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
                captured_at_utc=captured,
                record_id="lambda:gpu_8x_h100_sxm:0",
            )
        ],
        is_sample_data=sample,
    )


def test_non_sample_snapshot_accepted_for_first_launch_planning():
    report = validate_non_sample_price_snapshot(_snapshot(), max_age_days=30)

    assert report.non_sample_price_snapshot_passed is True
    assert report.launch_allowed is False


def test_sample_snapshot_still_blocks():
    report = validate_non_sample_price_snapshot(_snapshot(sample=True), max_age_days=30)

    assert report.non_sample_price_snapshot_passed is False
    assert "price snapshot is sample data" in report.blockers
