import json

from decodilo.lambda_cloud.api_models import LambdaInstanceType
from decodilo.lambda_cloud.live_discovery_report import LambdaLiveDiscoveryReport
from decodilo.lambda_cloud.shape_matcher import match_lambda_shape
from decodilo.pricing.snapshots import PriceSnapshot, PriceSourceType, SnapshotPriceRecord


def _snapshot(*records: SnapshotPriceRecord) -> PriceSnapshot:
    return PriceSnapshot(
        snapshot_id="snap",
        provider="lambda",
        captured_at_utc="2026-06-16T00:00:00Z",
        source_type=PriceSourceType.MANUAL_JSON,
        source_sha256="0" * 64,
        records=list(records),
        is_sample_data=False,
    )


def _record(instance_type: str = "gpu_8x_h100_sxm") -> SnapshotPriceRecord:
    return SnapshotPriceRecord(
        provider="lambda",
        instance_type=instance_type,
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        region="sample-offline",
        price_per_gpu_hour=2.5,
        price_per_instance_hour=20.0,
        captured_at_utc="2026-06-16T00:00:00Z",
        record_id=f"lambda:{instance_type}:0",
    )


def _discovery(*shapes: LambdaInstanceType) -> LambdaLiveDiscoveryReport:
    return LambdaLiveDiscoveryReport(live_api_used=True, instance_types=list(shapes))


def _shape(instance_type: str = "gpu_8x_h100_sxm") -> LambdaInstanceType:
    return LambdaInstanceType(
        instance_type_id=instance_type,
        name=instance_type,
        gpu_type="H100 SXM",
        gpus=8,
        regions=["us-west-1"],
    )


def test_lambda_shape_matcher_matches_discovered_shape_to_price_record() -> None:
    match = match_lambda_shape(
        discovery=_discovery(_shape()),
        price_snapshot=_snapshot(_record()),
        requested_gpu_type="H100 SXM",
        requested_gpus_per_instance=8,
        requested_region="us-west-1",
        requested_instance_type="gpu_8x_h100_sxm",
    )

    assert match.match_status == "matched"
    assert match.matched_price_record_id == "lambda:gpu_8x_h100_sxm:0"
    assert json.loads(match.to_json())["launch_allowed"] is False


def test_lambda_shape_matcher_detects_missing_price_and_discovery() -> None:
    no_price = match_lambda_shape(
        discovery=_discovery(_shape()),
        price_snapshot=_snapshot(),
        requested_gpu_type="H100 SXM",
        requested_gpus_per_instance=8,
        requested_region="us-west-1",
        requested_instance_type="gpu_8x_h100_sxm",
    )
    priced_only = match_lambda_shape(
        discovery=_discovery(),
        price_snapshot=_snapshot(_record()),
        requested_gpu_type="H100 SXM",
        requested_gpus_per_instance=8,
        requested_region="us-west-1",
        requested_instance_type="gpu_8x_h100_sxm",
    )

    assert no_price.match_status == "discovered_but_no_price"
    assert priced_only.match_status == "priced_but_not_discovered"
    assert priced_only.errors


def test_lambda_shape_matcher_can_treat_empty_live_endpoint_as_inconclusive() -> None:
    match = match_lambda_shape(
        discovery=_discovery(),
        price_snapshot=_snapshot(_record()),
        requested_gpu_type="H100 SXM",
        requested_gpus_per_instance=8,
        requested_region="us-west-1",
        requested_instance_type="gpu_8x_h100_sxm",
        live_instance_types_endpoint_inconclusive=True,
    )

    assert match.match_status == "matched"
    assert match.warnings


def test_lambda_shape_matcher_fails_closed_on_ambiguous_price() -> None:
    match = match_lambda_shape(
        discovery=_discovery(_shape()),
        price_snapshot=_snapshot(_record(), _record("gpu_8x_h100_sxm")),
        requested_gpu_type="H100 SXM",
        requested_gpus_per_instance=8,
        requested_region="us-west-1",
        requested_instance_type="gpu_8x_h100_sxm",
    )

    assert match.match_status == "ambiguous"
    assert match.errors
