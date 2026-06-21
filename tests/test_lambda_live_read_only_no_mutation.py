import pytest

from decodilo.lambda_cloud.endpoint_policy import LambdaEndpoint, LambdaEndpointPolicy
from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError
from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient
from decodilo.lambda_cloud.real_read_only_transport import (
    LambdaHTTPResponse,
    RealReadOnlyLambdaTransport,
    RealReadOnlyTransportConfig,
)


def test_live_client_has_no_billable_mutation_path() -> None:
    client = LiveReadOnlyLambdaCloudClient(
        RealReadOnlyLambdaTransport(
            api_key="fixture-key",
            config=RealReadOnlyTransportConfig(live_read_only=True),
            http_getter=lambda request, timeout: LambdaHTTPResponse(200, b"[]"),
        )
    )

    for method in [
        client.launch_instance,
        client.terminate_instance,
        client.restart_instance,
        client.create_ssh_key,
        client.delete_ssh_key,
        client.create_filesystem,
        client.delete_filesystem,
    ]:
        with pytest.raises(LambdaMutationForbiddenError):
            method()


def test_endpoint_policy_rejects_all_non_get() -> None:
    policy = LambdaEndpointPolicy()

    for method in ["POST", "PUT", "PATCH", "DELETE"]:
        assert not policy.check(
            LambdaEndpoint(operation="list_instances", method=method, path="/instances")
        ).allowed
