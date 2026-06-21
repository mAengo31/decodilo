import json

from decodilo.lambda_cloud.shape_evidence import (
    LambdaShapeEvidence,
    build_lambda_shape_evidence_report,
)


def test_public_catalog_evidence_is_not_live_availability():
    evidence = LambdaShapeEvidence(
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        instance_type_or_shape="gpu_8x_h100_sxm",
        source_type="public_product_catalog",
        source_url="https://lambda.ai/instances",
        source_hash="a" * 64,
        is_product_catalog_evidence=True,
        confidence="high",
    )
    report = build_lambda_shape_evidence_report([evidence])

    assert report.first_launch_evidence_usable is True
    assert report.evidence_status == "inconclusive"
    assert "no live availability proof present" in report.warnings
    assert json.loads(report.to_json())["launch_allowed"] is False


def test_sample_shape_evidence_rejected_for_first_launch():
    evidence = LambdaShapeEvidence(
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        instance_type_or_shape="gpu_8x_h100_sxm",
        source_type="price_snapshot",
        source_hash="a" * 64,
        is_sample_data=True,
    )
    report = build_lambda_shape_evidence_report([evidence])

    assert report.first_launch_evidence_usable is False
    assert "sample evidence cannot support first launch" in report.blockers
