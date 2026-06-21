"""In-memory fake Lambda mutation-shaped transport."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from decodilo.lambda_cloud.fake_mutation_models import (
    FakeLambdaCreateFilesystemRequest,
    FakeLambdaCreateFilesystemResponse,
    FakeLambdaCreateSSHKeyRequest,
    FakeLambdaCreateSSHKeyResponse,
    FakeLambdaDeleteFilesystemRequest,
    FakeLambdaDeleteFilesystemResponse,
    FakeLambdaDeleteSSHKeyRequest,
    FakeLambdaDeleteSSHKeyResponse,
    FakeLambdaLaunchRequest,
    FakeLambdaLaunchResponse,
    FakeLambdaRestartRequest,
    FakeLambdaRestartResponse,
    FakeLambdaTerminateRequest,
    FakeLambdaTerminateResponse,
)

_REAL_LAMBDA_URL_MARKERS = (
    "cloud.lambdalabs.com",
    "lambda.ai",
    "lambdalabs.com/api",
)


@dataclass
class FakeLambdaMutationTransport:
    fake_mode: bool = True
    base_url: str | None = None
    api_key: str | None = None
    fake_mutating_operations: int = 0
    real_mutating_operations: int = 0
    billable_action_performed: bool = False
    launched_by_idempotency: dict[str, FakeLambdaLaunchResponse] = field(default_factory=dict)
    terminated_by_idempotency: dict[str, FakeLambdaTerminateResponse] = field(default_factory=dict)
    operation_log: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.fake_mode:
            raise ValueError("fake mutation transport requires fake_mode=true")
        if self.api_key is not None:
            raise ValueError("fake mutation transport must not accept real API keys")
        if self.base_url and any(marker in self.base_url for marker in _REAL_LAMBDA_URL_MARKERS):
            raise ValueError("fake mutation transport must not target real Lambda base URLs")

    def launch_instance(self, request: FakeLambdaLaunchRequest) -> FakeLambdaLaunchResponse:
        if request.idempotency_key in self.launched_by_idempotency:
            response = self.launched_by_idempotency[request.idempotency_key]
            self._record(request.operation, request.idempotency_key, idempotent=True)
            return response
        instance_id = request.requested_instance_id or _synthetic_id(
            "fake-i-",
            request.lifecycle_id,
            request.idempotency_key,
            str(request.resource_index),
        )
        response = FakeLambdaLaunchResponse(
            instance_id=instance_id,
            idempotency_key=request.idempotency_key,
            message="fake launch accepted locally",
        )
        self.launched_by_idempotency[request.idempotency_key] = response
        self._record(request.operation, request.idempotency_key)
        return response

    def terminate_instance(
        self,
        request: FakeLambdaTerminateRequest,
    ) -> FakeLambdaTerminateResponse:
        if request.idempotency_key in self.terminated_by_idempotency:
            response = self.terminated_by_idempotency[request.idempotency_key]
            self._record(request.operation, request.idempotency_key, idempotent=True)
            return response
        response = FakeLambdaTerminateResponse(
            instance_id=request.instance_id,
            idempotency_key=request.idempotency_key,
            message="fake terminate accepted locally",
        )
        self.terminated_by_idempotency[request.idempotency_key] = response
        self._record(request.operation, request.idempotency_key)
        return response

    def restart_instance(self, request: FakeLambdaRestartRequest) -> FakeLambdaRestartResponse:
        self._record(request.operation, request.idempotency_key)
        return FakeLambdaRestartResponse(
            instance_id=request.instance_id,
            idempotency_key=request.idempotency_key,
            message="fake restart modeled locally",
        )

    def create_ssh_key(
        self,
        request: FakeLambdaCreateSSHKeyRequest,
    ) -> FakeLambdaCreateSSHKeyResponse:
        self._record(request.operation, request.idempotency_key)
        return FakeLambdaCreateSSHKeyResponse(
            key_id=_synthetic_id("fake-key-", request.key_name, request.idempotency_key),
            idempotency_key=request.idempotency_key,
        )

    def delete_ssh_key(
        self,
        request: FakeLambdaDeleteSSHKeyRequest,
    ) -> FakeLambdaDeleteSSHKeyResponse:
        self._record(request.operation, request.idempotency_key)
        return FakeLambdaDeleteSSHKeyResponse(
            key_id=request.key_id,
            idempotency_key=request.idempotency_key,
        )

    def create_filesystem(
        self,
        request: FakeLambdaCreateFilesystemRequest,
    ) -> FakeLambdaCreateFilesystemResponse:
        self._record(request.operation, request.idempotency_key)
        return FakeLambdaCreateFilesystemResponse(
            filesystem_id=_synthetic_id(
                "fake-fs-",
                request.filesystem_name,
                request.idempotency_key,
            ),
            idempotency_key=request.idempotency_key,
        )

    def delete_filesystem(
        self,
        request: FakeLambdaDeleteFilesystemRequest,
    ) -> FakeLambdaDeleteFilesystemResponse:
        self._record(request.operation, request.idempotency_key)
        return FakeLambdaDeleteFilesystemResponse(
            filesystem_id=request.filesystem_id,
            idempotency_key=request.idempotency_key,
        )

    def _record(self, operation: str, idempotency_key: str, *, idempotent: bool = False) -> None:
        self.fake_mutating_operations += 1
        self.operation_log.append(
            {
                "operation": operation,
                "idempotency_key": idempotency_key,
                "idempotent_replay": idempotent,
                "fake_only": True,
                "real_lambda_api_used": False,
                "billable_action_performed": False,
            }
        )


def _synthetic_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()[:14]
    return f"{prefix}{digest}"
