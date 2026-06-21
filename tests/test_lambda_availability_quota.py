from decodilo.lambda_cloud.availability import estimate_lambda_availability
from decodilo.lambda_cloud.discovery import discover_lambda_from_client
from decodilo.lambda_cloud.fake_transport import FakeLambdaTransport
from decodilo.lambda_cloud.quota_model import evaluate_lambda_quota
from decodilo.lambda_cloud.read_only_client import ReadOnlyLambdaCloudClient


def test_lambda_availability_and_quota_are_fixture_only() -> None:
    discovery = discover_lambda_from_client(
        ReadOnlyLambdaCloudClient(FakeLambdaTransport(fixtures_dir="tests/fixtures/lambda_cloud"))
    )
    availability = estimate_lambda_availability(
        discovery,
        region_id="us-west-1",
        gpu_type="H100 SXM",
        gpus_per_instance=8,
    )
    quota = evaluate_lambda_quota(
        discovery.quota,
        requested_instances=1,
        requested_gpus=8,
    )

    assert availability.available
    assert availability.live_api_used is False
    assert quota.quota_allows_request
    assert quota.live_api_used is False
