from decodilo.lambda_cloud.live_discovery import run_lambda_live_discovery
from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient
from decodilo.lambda_cloud.read_only_audit import audit_lambda_read_only
from decodilo.lambda_cloud.real_read_only_transport import (
    LambdaHTTPResponse,
    RealReadOnlyLambdaTransport,
    RealReadOnlyTransportConfig,
)


def test_lambda_live_discovery_calibration_records_no_mutation_or_billable_action() -> None:
    transport = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(live_read_only=True),
        http_getter=lambda request, timeout: LambdaHTTPResponse(200, b"[]"),
    )

    report = run_lambda_live_discovery(
        LiveReadOnlyLambdaCloudClient(transport),
        endpoint_set="minimal",
    )
    audit = audit_lambda_read_only(report.audit_log)

    assert all(result.method == "GET" for result in report.endpoint_results)
    assert all(not result.mutation for result in report.endpoint_results)
    assert report.summary.mutating_operations == 0
    assert report.billable_action_performed is False
    assert audit.status == "passed"
