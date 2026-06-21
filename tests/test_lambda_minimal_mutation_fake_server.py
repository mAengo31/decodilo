import pytest
from lambda_m027_helpers import fake_launch_request

from decodilo.lambda_cloud.minimal_mutation_fake_server import (
    LambdaMinimalMutationFakeServer,
)


def test_fake_server_launches_synthetic_instance():
    server = LambdaMinimalMutationFakeServer()
    response = server.launch_one_instance(fake_launch_request())

    assert response["instance_id"].startswith("fake-i-")
    assert response["real_lambda_api_used"] is False


def test_fake_server_binds_only_localhost():
    with pytest.raises(ValueError):
        LambdaMinimalMutationFakeServer(bind_host="0.0.0.0")
