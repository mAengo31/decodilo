"""Errors for the offline Lambda Cloud API boundary."""

from __future__ import annotations


class LambdaCloudError(RuntimeError):
    """Base error for offline Lambda Cloud planning code."""


class LambdaCloudDisabledError(LambdaCloudError):
    """Raised when a disabled Lambda client is used."""


class LambdaMutationForbiddenError(LambdaCloudError):
    """Raised when a mutating Lambda operation is attempted."""


class LambdaTransportError(LambdaCloudError):
    """Raised by the fake transport for simulated transport failures."""


class LambdaCredentialError(LambdaCloudError):
    """Raised when a credential model contains a raw-looking secret."""


class LambdaPreflightError(LambdaCloudError):
    """Raised for invalid Lambda preflight inputs."""
