import pytest
from lambda_m027_helpers import fake_launch_request, fake_terminate_request

from decodilo.lambda_cloud.fake_server_failure_modes import LambdaMinimalFakeFailure
from decodilo.lambda_cloud.minimal_mutation_fake_transport import (
    LambdaMinimalMutationFakeTransport,
)


def test_fake_launch_and_terminate_idempotent():
    transport = LambdaMinimalMutationFakeTransport()
    launch = fake_launch_request("idem-launch")

    first = transport.launch_one_instance(launch)
    second = transport.launch_one_instance(launch)

    assert first["instance_id"] == second["instance_id"]
    terminate = fake_terminate_request(first["instance_id"], "idem-terminate")
    terminated = transport.terminate_owned_instance(terminate)
    repeated = transport.terminate_owned_instance(terminate)
    assert terminated["lifecycle_state"] == repeated["lifecycle_state"] == "terminated"
    assert transport.real_mutating_operations == 0
    assert transport.billable_action_performed is False


def test_timeout_but_created_is_recoverable_by_reading_registry():
    transport = LambdaMinimalMutationFakeTransport()

    with pytest.raises(LambdaMinimalFakeFailure):
        transport.launch_one_instance(
            fake_launch_request("idem-timeout"),
            failure_mode="launch_timeout_but_created",
        )

    assert len(transport.registry.list_resources()) == 1


def test_real_lambda_url_and_credentials_rejected():
    with pytest.raises(ValueError):
        live_url = "https://" + "cloud.lambdalabs.com" + "/api"
        LambdaMinimalMutationFakeTransport(base_url=live_url)
    with pytest.raises(ValueError):
        LambdaMinimalMutationFakeTransport(credential_source="api-key")
