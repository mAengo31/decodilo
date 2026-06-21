import pytest

from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError
from decodilo.lambda_cloud.fake_transport import FakeLambdaTransport
from decodilo.lambda_cloud.mutation_guard import MUTATING_OPERATIONS, LambdaMutationGuard


def test_mutating_calls_denied_even_on_fake_transport() -> None:
    guard = LambdaMutationGuard()
    transport = FakeLambdaTransport()

    for operation in MUTATING_OPERATIONS:
        assert guard.check(operation).allowed is False
        with pytest.raises(LambdaMutationForbiddenError):
            transport.request(operation)
