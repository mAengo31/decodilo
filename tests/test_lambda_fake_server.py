import pytest

from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError
from decodilo.lambda_cloud.fake_server import FakeLambdaAPIServer


def test_fake_server_is_localhost_only() -> None:
    server = FakeLambdaAPIServer(host="127.0.0.1")

    assert server.info().bound_to_localhost_only is True
    assert server.handle("list_regions")[0]["region_id"] == "us-west-1"

    with pytest.raises(ValueError):
        FakeLambdaAPIServer(host="0.0.0.0")


def test_fake_server_mutating_endpoint_forbidden() -> None:
    server = FakeLambdaAPIServer()

    with pytest.raises(LambdaMutationForbiddenError):
        server.handle("terminate_instance")
