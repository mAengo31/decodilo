import pytest

from decodilo.lambda_cloud.fake_mutation_models import (
    FakeLambdaLaunchRequest,
    FakeLambdaTerminateRequest,
)
from decodilo.lambda_cloud.fake_mutation_server import (
    FakeLambdaMutationServer,
    FakeLambdaMutationServerConfig,
)


def test_fake_mutation_server_launch_and_terminate_envelopes() -> None:
    server = FakeLambdaMutationServer()
    launch = server.handle_launch(
        FakeLambdaLaunchRequest(
            lifecycle_id="life",
            resource_index=0,
            instance_type="gpu",
            region="us",
            idempotency_key="launch",
        )
    )
    terminate = server.handle_terminate(
        FakeLambdaTerminateRequest(
            instance_id=launch.response["instance_id"],
            idempotency_key="terminate",
        )
    )

    assert launch.ok is True
    assert terminate.response["lifecycle_state"] == "terminated"
    assert terminate.real_lambda_api_used is False


def test_fake_mutation_server_rejects_non_local_host() -> None:
    with pytest.raises(ValueError, match="127.0.0.1"):
        FakeLambdaMutationServer(FakeLambdaMutationServerConfig(host="0.0.0.0"))
