"""Error types for Lambda live read-only discovery."""

from __future__ import annotations

from decodilo.lambda_cloud.errors import (
    LambdaCloudError,
    LambdaMutationForbiddenError,
    LambdaTransportError,
)


class LambdaAuthError(LambdaTransportError):
    """Authentication or authorization failed for a read-only request."""


class LambdaRateLimitError(LambdaTransportError):
    """Lambda returned a rate-limit response."""


class LambdaServerError(LambdaTransportError):
    """Lambda returned a retryable server-side error."""


class LambdaMalformedResponseError(LambdaTransportError):
    """Lambda returned non-JSON or unexpected JSON."""


class LambdaEndpointDeniedError(LambdaMutationForbiddenError):
    """Endpoint policy denied the request before transport."""


class LambdaLiveAPIOptInRequiredError(LambdaCloudError):
    """Live read-only discovery was requested without explicit opt-in."""


class LambdaTimeoutError(LambdaTransportError):
    """A read-only request timed out."""


def redact_lambda_error_message(message: str, secret: str | None = None) -> str:
    if secret:
        return message.replace(secret, "<redacted>")
    return message
