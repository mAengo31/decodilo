from decodilo.lambda_cloud.fake_mutation_api import FakeLambdaMutationAPI
from decodilo.lambda_cloud.fake_mutation_models import (
    FakeLambdaLaunchRequest,
    FakeLambdaTerminateRequest,
)


def test_duplicate_fake_api_launch_is_idempotent() -> None:
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


def test_duplicate_fake_api_terminate_is_idempotent() -> None:
    api = FakeLambdaMutationAPI()
    request = FakeLambdaTerminateRequest(
        instance_id="fake-i-abc",
        idempotency_key="terminate",
    )

    first = api.fake_terminate_instance(request)
    second = api.fake_terminate_instance(request)

    assert first.instance_id == second.instance_id
    assert first.lifecycle_state == second.lifecycle_state == "terminated"
