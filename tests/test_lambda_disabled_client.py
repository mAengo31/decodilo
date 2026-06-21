import pytest

from decodilo.lambda_cloud.disabled_client import DisabledLambdaCloudClient
from decodilo.lambda_cloud.errors import LambdaCloudDisabledError


def test_disabled_lambda_client_rejects_reads_and_mutations() -> None:
    client = DisabledLambdaCloudClient()

    with pytest.raises(LambdaCloudDisabledError):
        client.list_instances()
    with pytest.raises(LambdaCloudDisabledError):
        client.launch_instance()
    with pytest.raises(LambdaCloudDisabledError):
        client.terminate_instance()
    with pytest.raises(LambdaCloudDisabledError):
        client.restart_instance()
