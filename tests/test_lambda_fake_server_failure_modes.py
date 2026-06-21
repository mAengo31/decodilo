import pytest
from lambda_m027_helpers import fake_launch_request, fake_terminate_request

from decodilo.lambda_cloud.minimal_mutation_fake_transport import (
    LambdaMinimalMutationFakeTransport,
)
from decodilo.lambda_cloud.minimal_mutation_response_parser import (
    parse_minimal_mutation_response,
)


def test_malformed_launch_response_rejected():
    transport = LambdaMinimalMutationFakeTransport()
    payload = transport.launch_one_instance(
        fake_launch_request(),
        failure_mode="malformed_launch_response",
    )

    with pytest.raises(ValueError):
        parse_minimal_mutation_response(payload)


def test_malformed_terminate_response_rejected():
    transport = LambdaMinimalMutationFakeTransport()
    launch = transport.launch_one_instance(fake_launch_request())
    payload = transport.terminate_owned_instance(
        fake_terminate_request(launch["instance_id"]),
        failure_mode="malformed_terminate_response",
    )

    with pytest.raises(ValueError):
        parse_minimal_mutation_response(payload)
