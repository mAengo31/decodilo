from decodilo.lambda_cloud.availability_evidence import build_lambda_availability_evidence
from decodilo.lambda_cloud.live_discovery_report import LambdaLiveDiscoveryReport


def test_zero_instance_types_is_endpoint_inconclusive():
    report = build_lambda_availability_evidence(
        LambdaLiveDiscoveryReport(
            live_api_used=True,
            instance_types=[],
            required_endpoint_success=True,
        )
    )

    assert report.status == "endpoint_inconclusive"
    assert report.instance_type_count == 0
    assert report.launch_allowed is False


def test_product_catalog_without_live_availability_remains_unknown():
    report = build_lambda_availability_evidence({"live_api_used": False})

    assert report.status == "not_checked"
    assert report.limitations
