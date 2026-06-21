from decodilo.lambda_cloud.availability_evidence import LambdaAvailabilityEvidence
from decodilo.lambda_cloud.launch_shape_resolution import LambdaLaunchShapeResolutionReport
from decodilo.lambda_cloud.non_sample_price_snapshot import LambdaNonSamplePriceSnapshotReport
from decodilo.lambda_cloud.shape_evidence import LambdaShapeEvidenceReport
from decodilo.lambda_cloud.shape_evidence_preflight import (
    build_lambda_shape_evidence_preflight,
)


def test_shape_evidence_preflight_passes_resolved_shape():
    report = build_lambda_shape_evidence_preflight(
        shape_evidence=LambdaShapeEvidenceReport(
            evidence_status="inconclusive",
            first_launch_evidence_usable=True,
            warnings=["no live availability proof present"],
        ),
        price_snapshot=LambdaNonSamplePriceSnapshotReport(
            price_snapshot_id="snap",
            is_sample_data=False,
            source_url_present=True,
            source_hash_present=True,
            captured_at_present=True,
            snapshot_age_days=0,
            non_sample_price_snapshot_passed=True,
        ),
        availability=LambdaAvailabilityEvidence(status="endpoint_inconclusive"),
        resolution=LambdaLaunchShapeResolutionReport(
            planned_gpu_type="H100 SXM",
            planned_gpus_per_instance=8,
            planned_instance_type_or_shape="gpu_8x_h100_sxm",
            live_availability_status="endpoint_inconclusive",
            shape_resolution_status="resolved",
            first_launch_allowed_by_shape_evidence=True,
        ),
    )

    assert report.preflight_passed is True
    assert report.shape_gate_passed is True
    assert report.price_gate_passed is True
    assert report.launch_allowed is False
