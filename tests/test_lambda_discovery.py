from decodilo.lambda_cloud.discovery import discover_lambda_from_client
from decodilo.lambda_cloud.fake_transport import FakeLambdaTransport
from decodilo.lambda_cloud.read_only_client import ReadOnlyLambdaCloudClient


def test_lambda_discovery_report_from_fake_transport() -> None:
    report = discover_lambda_from_client(
        ReadOnlyLambdaCloudClient(FakeLambdaTransport(fixtures_dir="tests/fixtures/lambda_cloud"))
    )

    assert report.live_api_used is False
    assert report.source == "fake_transport"
    assert len(report.regions) == 2
    assert len(report.running_instances) == 2
    assert report.quota is not None
