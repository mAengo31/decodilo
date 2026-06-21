from decodilo.lambda_cloud.live_discovery import run_lambda_live_discovery
from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient
from decodilo.lambda_cloud.real_read_only_transport import (
    LambdaHTTPResponse,
    RealReadOnlyLambdaTransport,
    RealReadOnlyTransportConfig,
)


def test_lambda_live_endpoint_coverage_minimal_fixture() -> None:
    def getter(request, timeout):  # noqa: ANN001
        if request.full_url.endswith("/instance-types"):
            return LambdaHTTPResponse(
                200,
                b'[{"instance_type_id":"gpu","name":"GPU","gpus":1}]',
            )
        if request.full_url.endswith("/instances"):
            return LambdaHTTPResponse(200, b"[]")
        return LambdaHTTPResponse(404, b"{}")

    transport = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(live_read_only=True),
        http_getter=getter,
    )
    report = run_lambda_live_discovery(
        LiveReadOnlyLambdaCloudClient(transport),
        endpoint_set="minimal",
    )

    assert report.endpoint_set == "minimal"
    assert report.endpoint_count_attempted == 2
    assert report.endpoint_count_succeeded == 2
    assert report.endpoint_coverage is not None
    assert report.endpoint_coverage.coverage_ratio == 1
    assert report.billable_action_performed is False
