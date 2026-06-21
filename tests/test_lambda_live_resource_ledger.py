from decodilo.lambda_cloud.launch_plan import build_lambda_launch_plan
from decodilo.lambda_cloud.live_discovery import run_lambda_live_discovery
from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient
from decodilo.lambda_cloud.live_resource_ledger import reconcile_lambda_live_resources
from decodilo.lambda_cloud.real_read_only_transport import (
    LambdaHTTPResponse,
    RealReadOnlyLambdaTransport,
    RealReadOnlyTransportConfig,
)


def test_lambda_live_resource_ledger_flags_unmanaged_without_mutation() -> None:
    def getter(request, timeout):  # noqa: ANN001
        if request.full_url.endswith("/instances"):
            return LambdaHTTPResponse(
                200,
                b'[{"instance_id":"i-unmanaged","status":"active","tags":{}}]',
            )
        return LambdaHTTPResponse(200, b"[]")

    discovery = run_lambda_live_discovery(
        LiveReadOnlyLambdaCloudClient(
            RealReadOnlyLambdaTransport(
                api_key="fixture-key",
                config=RealReadOnlyTransportConfig(live_read_only=True),
                http_getter=getter,
            )
        )
    )
    plan = build_lambda_launch_plan(
        run_id="run",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=1,
        max_run_budget=100,
    )

    ledger = reconcile_lambda_live_resources(discovery=discovery, launch_plan=plan)

    assert ledger.unmanaged_count == 1
    assert ledger.no_mutations_performed is True
    assert ledger.billable_action_performed is False
    assert not any("terminate " in action for action in ledger.advisory_actions)
