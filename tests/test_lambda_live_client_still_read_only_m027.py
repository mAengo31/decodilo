import pytest

from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError
from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient


def test_live_client_still_cannot_mutate_m027():
    client = LiveReadOnlyLambdaCloudClient(transport=None)  # type: ignore[arg-type]

    with pytest.raises(LambdaMutationForbiddenError):
        client.launch_instance()

    with pytest.raises(LambdaMutationForbiddenError):
        client.terminate_instance("fake-i-nope")
