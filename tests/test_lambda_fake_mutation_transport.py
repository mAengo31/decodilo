import pytest

from decodilo.lambda_cloud.fake_mutation_models import (
    FakeLambdaLaunchRequest,
    FakeLambdaRestartRequest,
    FakeLambdaTerminateRequest,
)
from decodilo.lambda_cloud.fake_mutation_transport import FakeLambdaMutationTransport


def test_fake_transport_launch_returns_synthetic_instance() -> None:
    transport = FakeLambdaMutationTransport()
    response = transport.launch_instance(
        FakeLambdaLaunchRequest(
            lifecycle_id="life",
            resource_index=0,
            instance_type="gpu",
            region="us",
            idempotency_key="k",
        )
    )

    assert response.instance_id.startswith("fake-i-")
    assert transport.real_mutating_operations == 0
    assert transport.billable_action_performed is False


def test_fake_transport_terminate_transitions_fake_instance() -> None:
    transport = FakeLambdaMutationTransport()
    response = transport.terminate_instance(
        FakeLambdaTerminateRequest(instance_id="fake-i-abc", idempotency_key="term")
    )

    assert response.lifecycle_state == "terminated"


def test_fake_transport_restart_is_modeled_but_local() -> None:
    transport = FakeLambdaMutationTransport()
    response = transport.restart_instance(
        FakeLambdaRestartRequest(instance_id="fake-i-abc", idempotency_key="restart")
    )

    assert response.lifecycle_state == "running"
    assert transport.real_mutating_operations == 0


def test_fake_transport_rejects_real_lambda_url() -> None:
    live_url = "https://" + "cloud.lambdalabs.com/api/v1"
    with pytest.raises(ValueError, match="real Lambda"):
        FakeLambdaMutationTransport(base_url=live_url)


def test_fake_transport_rejects_api_key() -> None:
    with pytest.raises(ValueError, match="API keys"):
        FakeLambdaMutationTransport(api_key="secret")


def test_fake_transport_rejects_non_fake_mode() -> None:
    with pytest.raises(ValueError, match="fake_mode"):
        FakeLambdaMutationTransport(fake_mode=False)
