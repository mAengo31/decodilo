import pytest

from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError, LambdaTransportError
from decodilo.lambda_cloud.fake_transport import FakeLambdaTransport


def test_fake_transport_returns_fixture_instance_types() -> None:
    transport = FakeLambdaTransport(fixtures_dir="tests/fixtures/lambda_cloud")

    payload = transport.request("list_instance_types")

    assert payload[0]["instance_type_id"] == "gpu_8x_h100_sxm"
    assert transport.metrics.read_requests == 1


def test_fake_transport_simulates_throttle_and_malformed_response() -> None:
    throttle = FakeLambdaTransport(failure_mode="throttle")
    malformed = FakeLambdaTransport(failure_mode="malformed")

    with pytest.raises(LambdaTransportError, match="429"):
        throttle.request("list_instances")
    assert malformed.request("list_instances") == {"malformed": True}


def test_fake_transport_forbids_mutating_endpoint() -> None:
    transport = FakeLambdaTransport()

    with pytest.raises(LambdaMutationForbiddenError):
        transport.request("launch_instance")
