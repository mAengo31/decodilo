import pytest

from decodilo.lambda_cloud.api_error_handling import (
    LambdaMalformedResponseError,
    LambdaRateLimitError,
)
from decodilo.lambda_cloud.api_rate_limit import RateLimitPolicy
from decodilo.lambda_cloud.endpoint_policy import LambdaEndpoint
from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError
from decodilo.lambda_cloud.real_read_only_transport import (
    LambdaHTTPResponse,
    RealReadOnlyLambdaTransport,
    RealReadOnlyTransportConfig,
)


def test_real_read_only_transport_get_allowed_endpoint_with_injected_getter() -> None:
    calls = []

    def getter(request, timeout):  # noqa: ANN001
        calls.append((request.full_url, request.get_method(), timeout))
        return LambdaHTTPResponse(200, b'[{"region_id":"us-west-1","name":"US West"}]')

    transport = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(
            base_url="http://127.0.0.1:9/api/v1",
            live_read_only=True,
        ),
        http_getter=getter,
    )

    payload = transport.request_json("list_regions")

    assert payload[0]["region_id"] == "us-west-1"
    assert calls[0][1] == "GET"
    assert transport.audit_log[0].secret_redacted


def test_real_read_only_transport_disallowed_endpoint_before_getter() -> None:
    def getter(request, timeout):  # noqa: ANN001
        raise AssertionError("getter should not run")

    transport = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(live_read_only=True),
        http_getter=getter,
    )

    with pytest.raises(LambdaMutationForbiddenError):
        transport._authorize_endpoint(  # noqa: SLF001 - unit verifies pre-transport guard
            LambdaEndpoint(operation="unknown", method="GET", path="/unknown")
        )


def test_real_read_only_transport_handles_malformed_and_rate_limit() -> None:
    malformed = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(live_read_only=True),
        http_getter=lambda request, timeout: LambdaHTTPResponse(200, b"not-json"),
    )
    with pytest.raises(LambdaMalformedResponseError):
        malformed.request_json("list_regions")

    rate_limited = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(
            live_read_only=True,
            rate_limit_policy=RateLimitPolicy(max_attempts=1),
        ),
        http_getter=lambda request, timeout: LambdaHTTPResponse(429, b"{}"),
    )
    with pytest.raises(LambdaRateLimitError):
        rate_limited.request_json("list_regions")


def test_real_read_only_transport_429_retries_then_succeeds() -> None:
    attempts = {"count": 0}

    def getter(request, timeout):  # noqa: ANN001
        attempts["count"] += 1
        if attempts["count"] == 1:
            return LambdaHTTPResponse(429, b"{}")
        return LambdaHTTPResponse(200, b"[]")

    transport = RealReadOnlyLambdaTransport(
        api_key="fixture-key",
        config=RealReadOnlyTransportConfig(live_read_only=True),
        http_getter=getter,
    )

    assert transport.request_json("list_regions") == []
    assert attempts["count"] == 2
