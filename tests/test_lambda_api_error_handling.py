import pytest

from decodilo.lambda_cloud.api_error_handling import LambdaAuthError, LambdaTimeoutError
from decodilo.lambda_cloud.real_read_only_transport import (
    LambdaHTTPResponse,
    RealReadOnlyLambdaTransport,
    RealReadOnlyTransportConfig,
)


def test_lambda_auth_error_does_not_retry() -> None:
    attempts = {"count": 0}

    def getter(request, timeout):  # noqa: ANN001
        attempts["count"] += 1
        return LambdaHTTPResponse(401, b"{}")

    transport = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(live_read_only=True),
        http_getter=getter,
    )

    with pytest.raises(LambdaAuthError):
        transport.request_json("list_regions")
    assert attempts["count"] == 1


def test_lambda_timeout_error_redacted() -> None:
    def getter(request, timeout):  # noqa: ANN001
        raise TimeoutError("timed out")

    transport = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(live_read_only=True),
        http_getter=getter,
    )

    with pytest.raises(LambdaTimeoutError) as exc:
        transport.request_json("list_regions")
    assert "fixture-key" not in str(exc.value)
