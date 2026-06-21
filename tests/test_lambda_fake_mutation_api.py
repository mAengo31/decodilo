from decodilo.lambda_cloud.fake_mutation_api import FakeLambdaMutationAPI
from decodilo.lambda_cloud.fake_mutation_models import (
    FakeLambdaLaunchRequest,
    FakeLambdaTerminateRequest,
)


def test_fake_mutation_api_launch_and_terminate() -> None:
    api = FakeLambdaMutationAPI()
    launch = api.fake_launch_instance(
        FakeLambdaLaunchRequest(
            lifecycle_id="life",
            resource_index=0,
            instance_type="gpu",
            region="us",
            idempotency_key="launch",
        )
    )
    terminate = api.fake_terminate_instance(
        FakeLambdaTerminateRequest(
            instance_id=launch.instance_id,
            idempotency_key="terminate",
        )
    )

    assert launch.instance_id.startswith("fake-i-")
    assert terminate.lifecycle_state == "terminated"
    assert api.transport.real_mutating_operations == 0


def test_fake_mutation_api_launch_idempotency() -> None:
    api = FakeLambdaMutationAPI()
    request = FakeLambdaLaunchRequest(
        lifecycle_id="life",
        resource_index=0,
        instance_type="gpu",
        region="us",
        idempotency_key="launch",
    )

    first = api.fake_launch_instance(request)
    second = api.fake_launch_instance(request)

    assert first.instance_id == second.instance_id
    assert api.transport.fake_mutating_operations == 2
