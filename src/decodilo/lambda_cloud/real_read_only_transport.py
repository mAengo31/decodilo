"""Real Lambda HTTP transport constrained to read-only GET requests."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.api_error_handling import (
    LambdaAuthError,
    LambdaEndpointDeniedError,
    LambdaMalformedResponseError,
    LambdaRateLimitError,
    LambdaServerError,
    LambdaTimeoutError,
)
from decodilo.lambda_cloud.api_rate_limit import RateLimitPolicy
from decodilo.lambda_cloud.endpoint_policy import (
    LambdaEndpoint,
    LambdaEndpointPolicy,
    endpoint_for_operation,
)
from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError
from decodilo.lambda_cloud.mutation_guard import LambdaMutationGuard
from decodilo.lambda_cloud.read_only_audit import LambdaReadOnlyAuditEntry


class RealReadOnlyTransportConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: str = "https://cloud.lambdalabs.com/api/v1"
    timeout_seconds: float = Field(default=10.0, gt=0)
    live_read_only: bool = False
    user_agent: str = "decodilo-lambda-read-only-discovery/0.1"
    rate_limit_policy: RateLimitPolicy = Field(default_factory=RateLimitPolicy)


@dataclass(frozen=True)
class LambdaHTTPResponse:
    status_code: int
    body: bytes


HTTPGetter = Callable[[Request, float], LambdaHTTPResponse]


class RealReadOnlyLambdaTransport:
    """Minimal live HTTP transport guarded before every request."""

    def __init__(
        self,
        *,
        api_key: str,
        config: RealReadOnlyTransportConfig,
        endpoint_policy: LambdaEndpointPolicy | None = None,
        mutation_guard: LambdaMutationGuard | None = None,
        http_getter: HTTPGetter | None = None,
    ) -> None:
        if not config.live_read_only:
            raise LambdaEndpointDeniedError(
                "live Lambda read-only transport requires explicit live_read_only opt-in"
            )
        self._api_key = api_key
        self.config = config
        self.endpoint_policy = endpoint_policy or LambdaEndpointPolicy()
        self.mutation_guard = mutation_guard or LambdaMutationGuard()
        self.http_getter = http_getter or _default_http_getter
        self.audit_log: list[LambdaReadOnlyAuditEntry] = []

    def request_json(
        self,
        operation: str,
        *,
        instance_id: str | None = None,
    ) -> Any:
        endpoint = endpoint_for_operation(operation, instance_id=instance_id)
        self._authorize_endpoint(endpoint)
        last_error: Exception | None = None
        attempts = self.config.rate_limit_policy.max_attempts
        for attempt in range(1, attempts + 1):
            request = self._build_request(endpoint)
            try:
                response = self.http_getter(request, self.config.timeout_seconds)
                if response.status_code >= 400:
                    self._record(endpoint, response.status_code, error=str(response.status_code))
                    last_error = _error_for_status(response.status_code, secret=self._api_key)
                    if self.config.rate_limit_policy.should_retry(
                        status_code=response.status_code,
                        attempt=attempt,
                    ):
                        _maybe_sleep(self.config.rate_limit_policy.base_delay_seconds)
                        continue
                    raise last_error
                payload = self._decode_response(response, endpoint)
                self._record(endpoint, response.status_code)
                return payload
            except HTTPError as exc:
                status = exc.code
                self._record(endpoint, status, error=str(status))
                last_error = _error_for_status(status, secret=self._api_key)
                if not self.config.rate_limit_policy.should_retry(
                    status_code=status,
                    attempt=attempt,
                ):
                    raise last_error from exc
                _maybe_sleep(self.config.rate_limit_policy.base_delay_seconds)
            except TimeoutError as exc:
                self._record(endpoint, None, error="timeout")
                raise LambdaTimeoutError("Lambda read-only request timed out") from exc
            except URLError as exc:
                self._record(endpoint, None, error="url_error")
                raise LambdaTimeoutError("Lambda read-only request failed or timed out") from exc
        if last_error is not None:
            raise last_error
        raise LambdaServerError("Lambda read-only request failed")

    def _authorize_endpoint(self, endpoint: LambdaEndpoint) -> None:
        mutation = self.mutation_guard.check(endpoint.operation)
        if not mutation.allowed:
            raise LambdaMutationForbiddenError(mutation.reason)
        policy = self.endpoint_policy.check(endpoint)
        if not policy.allowed:
            raise LambdaEndpointDeniedError(policy.reason)

    def _build_request(self, endpoint: LambdaEndpoint) -> Request:
        path = endpoint.path.lstrip("/")
        url = urljoin(self.config.base_url.rstrip("/") + "/", path)
        return Request(
            url,
            method="GET",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "User-Agent": self.config.user_agent,
                "Accept": "application/json",
            },
        )

    def _decode_response(self, response: LambdaHTTPResponse, endpoint: LambdaEndpoint) -> Any:
        try:
            return json.loads(response.body.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise LambdaMalformedResponseError("Lambda response was not valid JSON") from exc

    def _record(
        self,
        endpoint: LambdaEndpoint,
        status_code: int | None,
        *,
        error: str | None = None,
    ) -> None:
        self.audit_log.append(
            LambdaReadOnlyAuditEntry(
                operation=endpoint.operation,
                method=endpoint.method,
                endpoint=endpoint.path,
                allowed=True,
                status_code=status_code,
                live_api_used=True,
                mutation=False,
                request_body_present=False,
                secret_redacted=True,
                error=error,
            )
        )


def _default_http_getter(request: Request, timeout_seconds: float) -> LambdaHTTPResponse:
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - guarded GET only
        return LambdaHTTPResponse(
            status_code=int(response.status),
            body=response.read(),
        )


def _error_for_status(status_code: int, *, secret: str) -> Exception:
    if status_code in {401, 403}:
        return LambdaAuthError("Lambda authentication failed")
    if status_code == 429:
        return LambdaRateLimitError("Lambda rate limit reached")
    if status_code >= 500:
        return LambdaServerError("Lambda server error")
    return LambdaEndpointDeniedError(f"Lambda endpoint denied or unsupported: {status_code}")


def _maybe_sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)
