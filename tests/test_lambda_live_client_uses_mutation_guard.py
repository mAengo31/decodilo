import pytest

from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError
from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient
from decodilo.lambda_cloud.real_read_only_transport import (
    LambdaHTTPResponse,
    RealReadOnlyLambdaTransport,
    RealReadOnlyTransportConfig,
)


def test_live_client_uses_guard_and_rejects_mutations() -> None:
    transport = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(live_read_only=True),
        http_getter=lambda request, timeout: LambdaHTTPResponse(200, b"[]"),
    )
    client = LiveReadOnlyLambdaCloudClient(transport)

    assert client.list_regions() == []
    with pytest.raises(LambdaMutationForbiddenError):
        client.launch_instance()
    with pytest.raises(LambdaMutationForbiddenError):
        client.terminate_instance()
