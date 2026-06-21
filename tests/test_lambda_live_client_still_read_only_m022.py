import pytest

from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError
from decodilo.lambda_cloud.live_read_only_client import LiveReadOnlyLambdaCloudClient


def test_live_client_still_raises_for_mutation_methods_m022() -> None:
    client = LiveReadOnlyLambdaCloudClient(transport=None)  # type: ignore[arg-type]

    for method_name in [
        "launch_instance",
        "terminate_instance",
        "restart_instance",
        "create_ssh_key",
        "delete_ssh_key",
        "create_filesystem",
        "delete_filesystem",
    ]:
        with pytest.raises(LambdaMutationForbiddenError):
            getattr(client, method_name)()
