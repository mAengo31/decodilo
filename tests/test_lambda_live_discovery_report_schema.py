from decodilo.lambda_cloud.live_discovery import run_lambda_live_discovery
from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient
from decodilo.lambda_cloud.real_read_only_transport import (
    LambdaHTTPResponse,
    RealReadOnlyLambdaTransport,
    RealReadOnlyTransportConfig,
)


def test_lambda_live_discovery_report_schema_and_flags() -> None:
    transport = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(live_read_only=True),
        http_getter=lambda request, timeout: LambdaHTTPResponse(200, b"[]"),
    )
    report = run_lambda_live_discovery(LiveReadOnlyLambdaCloudClient(transport))

    assert report.live_api_used is True
    assert report.read_only_mode is True
    assert report.mutation_guard_enabled is True
    assert report.endpoint_policy_enabled is True
    assert report.billable_action_performed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.to_json()
