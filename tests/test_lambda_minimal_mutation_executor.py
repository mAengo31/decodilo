import pytest
from lambda_m027_helpers import fake_context, fake_launch_request, fake_terminate_request

from decodilo.lambda_cloud.minimal_mutation_execution_context import (
    build_fake_server_execution_context,
)
from decodilo.lambda_cloud.minimal_mutation_executor import LambdaMinimalMutationExecutor


def test_executor_fake_launch_and_terminate():
    executor = LambdaMinimalMutationExecutor(context=fake_context())
    launch = executor.execute_launch(fake_launch_request())
    terminate = executor.execute_terminate(fake_terminate_request(launch.instance_id))

    assert launch.instance_id.startswith("fake-i-")
    assert terminate.termination_verified is True
    assert executor.transport.real_mutating_operations == 0


def test_executor_blocks_missing_evidence():
    executor = LambdaMinimalMutationExecutor(
        context=fake_context(),
        budget_lock_present=False,
    )

    with pytest.raises(ValueError):
        executor.execute_launch(fake_launch_request())


def test_executor_blocks_real_lambda_url():
    with pytest.raises(ValueError):
        live_url = "https://" + "cloud.lambdalabs.com" + "/api"
        build_fake_server_execution_context(base_url=live_url)
