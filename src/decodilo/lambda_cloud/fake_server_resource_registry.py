"""In-memory registry for the M027 fake minimal mutation server."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class LambdaFakeServerResource(BaseModel):
    model_config = ConfigDict(frozen=True)

    instance_id: str
    instance_type: str
    region: str
    lifecycle_state: str = "running"
    launch_idempotency_key: str
    terminate_idempotency_key: str | None = None
    fake_only: bool = True
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False


@dataclass
class LambdaFakeServerResourceRegistry:
    resources: dict[str, LambdaFakeServerResource] = field(default_factory=dict)
    launch_by_key: dict[str, str] = field(default_factory=dict)
    terminate_by_key: dict[str, str] = field(default_factory=dict)

    def launch(
        self,
        *,
        instance_type: str,
        region: str,
        idempotency_key: str,
    ) -> LambdaFakeServerResource:
        if idempotency_key in self.launch_by_key:
            return self.resources[self.launch_by_key[idempotency_key]]
        instance_id = _synthetic_instance_id(instance_type, region, idempotency_key)
        resource = LambdaFakeServerResource(
            instance_id=instance_id,
            instance_type=instance_type,
            region=region,
            launch_idempotency_key=idempotency_key,
        )
        self.resources[instance_id] = resource
        self.launch_by_key[idempotency_key] = instance_id
        return resource

    def terminate(self, *, instance_id: str, idempotency_key: str) -> LambdaFakeServerResource:
        if idempotency_key in self.terminate_by_key:
            return self.resources[self.terminate_by_key[idempotency_key]]
        if instance_id not in self.resources:
            raise ValueError("cannot terminate unknown fake instance")
        current = self.resources[instance_id]
        terminated = current.model_copy(
            update={
                "lifecycle_state": "terminated",
                "terminate_idempotency_key": idempotency_key,
            }
        )
        self.resources[instance_id] = terminated
        self.terminate_by_key[idempotency_key] = instance_id
        return terminated

    def get(self, instance_id: str) -> LambdaFakeServerResource | None:
        return self.resources.get(instance_id)

    def list_resources(self) -> list[LambdaFakeServerResource]:
        return list(self.resources.values())


class LambdaFakeServerResourceRegistryReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    resources: list[LambdaFakeServerResource] = Field(default_factory=list)
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _synthetic_instance_id(*parts: str) -> str:
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()[:14]
    return f"fake-i-{digest}"


def write_lambda_fake_server_resource_registry_report(
    path: str | Path,
    report: LambdaFakeServerResourceRegistryReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
