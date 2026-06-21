import pytest

from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError, LambdaTransportError
from decodilo.lambda_cloud.fake_transport import FakeLambdaTransport
from decodilo.lambda_cloud.read_only_client import ReadOnlyLambdaCloudClient


def test_read_only_client_reads_fixture_data() -> None:
    client = ReadOnlyLambdaCloudClient(
        FakeLambdaTransport(fixtures_dir="tests/fixtures/lambda_cloud")
    )

    assert client.list_instances()[0].instance_id == "i-fixture-managed"
    assert client.get_quota().max_gpus == 16
    assert client.get_usage_estimate().estimated_hourly_cost == 1.5


def test_read_only_client_mutations_raise_forbidden() -> None:
    client = ReadOnlyLambdaCloudClient(FakeLambdaTransport())

    with pytest.raises(LambdaMutationForbiddenError):
        client.launch_instance()


def test_read_only_client_rejects_malformed_response() -> None:
    client = ReadOnlyLambdaCloudClient(FakeLambdaTransport(failure_mode="malformed"))

    with pytest.raises(LambdaTransportError):
        client.list_instances()
