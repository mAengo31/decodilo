"""Read-only Lambda Cloud client backed by the local fake transport."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from decodilo.lambda_cloud.api_models import (
    LambdaFilesystem,
    LambdaImage,
    LambdaInstance,
    LambdaInstanceType,
    LambdaQuota,
    LambdaRegion,
    LambdaSSHKey,
    LambdaUsageEstimate,
)
from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError, LambdaTransportError
from decodilo.lambda_cloud.fake_transport import FakeLambdaTransport
from decodilo.lambda_cloud.mutation_guard import LambdaMutationGuard

T = TypeVar("T", bound=BaseModel)


class ReadOnlyLambdaCloudClient:
    """Read-only client for fixture/fake transport discovery."""

    def __init__(self, transport: FakeLambdaTransport) -> None:
        self.transport = transport
        self._guard = LambdaMutationGuard()

    def list_instance_types(self) -> list[LambdaInstanceType]:
        return self._list("list_instance_types", LambdaInstanceType)

    def list_regions(self) -> list[LambdaRegion]:
        return self._list("list_regions", LambdaRegion)

    def list_images(self) -> list[LambdaImage]:
        return self._list("list_images", LambdaImage)

    def list_ssh_keys(self) -> list[LambdaSSHKey]:
        return self._list("list_ssh_keys", LambdaSSHKey)

    def list_filesystems(self) -> list[LambdaFilesystem]:
        return self._list("list_filesystems", LambdaFilesystem)

    def list_instances(self) -> list[LambdaInstance]:
        return self._list("list_instances", LambdaInstance)

    def get_instance(self, instance_id: str) -> LambdaInstance:
        payload = self.transport.request("get_instance", {"instance_id": instance_id})
        if not isinstance(payload, dict):
            raise LambdaTransportError("malformed get_instance response")
        return LambdaInstance.model_validate(payload)

    def get_quota(self) -> LambdaQuota:
        payload = self.transport.request("get_quota")
        if not isinstance(payload, dict):
            raise LambdaTransportError("malformed get_quota response")
        return LambdaQuota.model_validate(payload)

    def get_usage_estimate(self) -> LambdaUsageEstimate:
        payload = self.transport.request("get_usage_estimate")
        if not isinstance(payload, dict):
            raise LambdaTransportError("malformed get_usage_estimate response")
        return LambdaUsageEstimate.model_validate(payload)

    def launch_instance(self, *args: object, **kwargs: object) -> None:
        self._forbid("launch_instance")

    def terminate_instance(self, *args: object, **kwargs: object) -> None:
        self._forbid("terminate_instance")

    def restart_instance(self, *args: object, **kwargs: object) -> None:
        self._forbid("restart_instance")

    def create_ssh_key(self, *args: object, **kwargs: object) -> None:
        self._forbid("create_ssh_key")

    def delete_ssh_key(self, *args: object, **kwargs: object) -> None:
        self._forbid("delete_ssh_key")

    def create_filesystem(self, *args: object, **kwargs: object) -> None:
        self._forbid("create_filesystem")

    def delete_filesystem(self, *args: object, **kwargs: object) -> None:
        self._forbid("delete_filesystem")

    def _list(self, operation: str, model: type[T]) -> list[T]:
        payload = self.transport.request(operation)
        if not isinstance(payload, list):
            raise LambdaTransportError(f"malformed {operation} response")
        return [model.model_validate(item) for item in payload]

    def _forbid(self, operation: str) -> None:
        report = self._guard.check(operation)
        raise LambdaMutationForbiddenError(report.reason)


def read_only_client_from_fixtures(fixtures_dir: str | None = None) -> ReadOnlyLambdaCloudClient:
    return ReadOnlyLambdaCloudClient(FakeLambdaTransport(fixtures_dir=fixtures_dir))


def ensure_read_only_payload(value: Any) -> Any:
    """Small helper for tests that need to assert payloads are data-only."""

    return value
