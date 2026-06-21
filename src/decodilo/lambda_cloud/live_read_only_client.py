"""Live read-only Lambda client using the guarded transport."""

from __future__ import annotations

from typing import TypeVar

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
from decodilo.lambda_cloud.errors import LambdaMutationForbiddenError
from decodilo.lambda_cloud.live_instance_type_parser import (
    parse_lambda_live_instance_types,
)
from decodilo.lambda_cloud.real_read_only_transport import RealReadOnlyLambdaTransport

T = TypeVar("T", bound=BaseModel)


class LiveReadOnlyLambdaCloudClient:
    """Read/list/get-only Lambda client.

    Mutating methods are intentionally present only to raise if called through
    shared protocol code.
    """

    def __init__(self, transport: RealReadOnlyLambdaTransport) -> None:
        self.transport = transport

    @property
    def audit_log(self):
        return self.transport.audit_log

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
        payload = self.transport.request_json("get_instance", instance_id=instance_id)
        return LambdaInstance.model_validate(_unwrap_payload(payload))

    def get_quota(self) -> LambdaQuota:
        return LambdaQuota.model_validate(_unwrap_payload(self.transport.request_json("get_quota")))

    def get_usage_estimate(self) -> LambdaUsageEstimate:
        return LambdaUsageEstimate.model_validate(
            _unwrap_payload(self.transport.request_json("get_usage_estimate"))
        )

    def launch_instance(self, *args: object, **kwargs: object) -> None:
        raise LambdaMutationForbiddenError("Lambda launch is forbidden in read-only client")

    def terminate_instance(self, *args: object, **kwargs: object) -> None:
        raise LambdaMutationForbiddenError("Lambda terminate is forbidden in read-only client")

    def restart_instance(self, *args: object, **kwargs: object) -> None:
        raise LambdaMutationForbiddenError("Lambda restart is forbidden in read-only client")

    def create_ssh_key(self, *args: object, **kwargs: object) -> None:
        raise LambdaMutationForbiddenError("Lambda SSH key creation is forbidden")

    def delete_ssh_key(self, *args: object, **kwargs: object) -> None:
        raise LambdaMutationForbiddenError("Lambda SSH key deletion is forbidden")

    def create_filesystem(self, *args: object, **kwargs: object) -> None:
        raise LambdaMutationForbiddenError("Lambda filesystem creation is forbidden")

    def delete_filesystem(self, *args: object, **kwargs: object) -> None:
        raise LambdaMutationForbiddenError("Lambda filesystem deletion is forbidden")

    def _list(self, operation: str, model: type[T]) -> list[T]:
        payload = _unwrap_payload(self.transport.request_json(operation))
        if operation == "list_instance_types" and isinstance(payload, dict):
            payload = _coerce_instance_type_map(payload)
        if isinstance(payload, dict):
            payload = payload.get("data") or payload.get("items") or payload.get("results") or []
        return [model.model_validate(item) for item in payload]


def _unwrap_payload(payload):
    if isinstance(payload, dict) and "data" in payload and len(payload) <= 2:
        return payload["data"]
    return payload


def _coerce_instance_type_map(payload: dict) -> list[dict]:
    """Coerce Lambda's map-shaped /instance-types response into local models."""

    parsed = parse_lambda_live_instance_types(payload)
    return [
        {
            "instance_type_id": record.instance_type_name,
            "name": record.instance_type_name,
            "gpu_type": record.gpu_description,
            "gpus": _gpu_count(record.instance_type_name),
            "price_per_hour": record.price_per_hour,
            "regions": record.available_regions,
            "metadata": {
                "live_instance_type_payload_shape": parsed.response_shape,
                "regions_with_capacity_available": record.available_regions,
            },
        }
        for record in parsed.parsed_instance_types
    ]


def _gpu_count(name: str) -> int:
    if not name.startswith("gpu_"):
        return 0
    prefix = name.removeprefix("gpu_").split("x_", 1)[0]
    try:
        return int(prefix)
    except ValueError:
        return 0
