"""Typed offline models for Lambda Cloud API fixture data."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaInstanceStatus = Literal[
    "booting",
    "pending",
    "running",
    "active",
    "stopped",
    "stopping",
    "terminated",
    "terminating",
    "unknown",
]


class LambdaFixtureModel(BaseModel):
    """Base model that preserves fixture fields unknown to this milestone."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _move_unknown_fields_to_metadata(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        known = set(cls.model_fields)
        metadata = dict(data.get("metadata") or {})
        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            if key == "metadata":
                continue
            if key in known:
                cleaned[key] = value
            else:
                metadata[key] = value
        cleaned["metadata"] = metadata
        return cleaned

    def stable_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaInstanceType(LambdaFixtureModel):
    instance_type_id: str
    name: str
    gpu_type: str | None = None
    gpus: int = Field(default=0, ge=0)
    memory_gb: float | None = Field(default=None, ge=0)
    vcpus: int | None = Field(default=None, ge=0)
    price_per_hour: float | None = Field(default=None, ge=0)
    regions: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_live_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "instance_type_id" not in data and isinstance(data.get("name"), str):
            data = {**data, "instance_type_id": data["name"]}
        return data


class LambdaRegion(LambdaFixtureModel):
    region_id: str
    name: str
    available: bool = True

    @model_validator(mode="before")
    @classmethod
    def _coerce_live_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "region_id" not in data and isinstance(data.get("name"), str):
            data = {**data, "region_id": data["name"]}
        return data


class LambdaImage(LambdaFixtureModel):
    image_id: str
    name: str
    description: str | None = None
    family: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_live_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "image_id" not in data and isinstance(data.get("id"), str):
            data = {**data, "image_id": data["id"]}
        if "image_id" not in data and isinstance(data.get("name"), str):
            data = {**data, "image_id": data["name"]}
        return data


class LambdaSSHKey(LambdaFixtureModel):
    key_id: str
    name: str
    public_key_fingerprint: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_live_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        coerced = dict(data)
        if "key_id" not in coerced and isinstance(coerced.get("id"), str):
            coerced["key_id"] = coerced["id"]
        if "key_id" not in coerced and isinstance(coerced.get("name"), str):
            coerced["key_id"] = coerced["name"]
        public_key = coerced.pop("public_key", None)
        if isinstance(public_key, str):
            digest = hashlib.sha256(public_key.encode("utf-8")).hexdigest()[:16]
            coerced.setdefault("public_key_fingerprint", f"SHA256:{digest}")
            metadata = dict(coerced.get("metadata") or {})
            metadata["public_key_redacted"] = True
            coerced["metadata"] = metadata
        return coerced


class LambdaFilesystem(LambdaFixtureModel):
    filesystem_id: str
    name: str
    region_id: str | None = None
    size_gb: float | None = Field(default=None, ge=0)
    mounted: bool = False

    @model_validator(mode="before")
    @classmethod
    def _coerce_live_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "filesystem_id" not in data and isinstance(data.get("id"), str):
            data = {**data, "filesystem_id": data["id"]}
        if "filesystem_id" not in data and isinstance(data.get("name"), str):
            data = {**data, "filesystem_id": data["name"]}
        return data


class LambdaInstance(LambdaFixtureModel):
    instance_id: str
    name: str | None = None
    instance_type_id: str | None = None
    region_id: str | None = None
    image_id: str | None = None
    status: LambdaInstanceStatus = "unknown"
    ssh_key_id: str | None = None
    filesystem_ids: list[str] = Field(default_factory=list)
    owner: str | None = None
    hourly_cost: float | None = Field(default=None, ge=0)
    tags: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _coerce_live_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        coerced = dict(data)
        if "instance_id" not in coerced and isinstance(coerced.get("id"), str):
            coerced["instance_id"] = coerced["id"]
        if "instance_id" not in coerced and isinstance(coerced.get("name"), str):
            coerced["instance_id"] = coerced["name"]
        if "instance_type_id" not in coerced and isinstance(coerced.get("instance_type"), str):
            coerced["instance_type_id"] = coerced["instance_type"]
        return coerced


class LambdaQuota(LambdaFixtureModel):
    max_instances: int | None = Field(default=None, ge=0)
    max_gpus: int | None = Field(default=None, ge=0)
    running_instances: int = Field(default=0, ge=0)
    running_gpus: int = Field(default=0, ge=0)


class LambdaUsageEstimate(LambdaFixtureModel):
    estimated_hourly_cost: float = Field(default=0.0, ge=0)
    estimated_monthly_cost: float | None = Field(default=None, ge=0)
    running_instance_count: int = Field(default=0, ge=0)
    source: Literal["fixture", "fake_transport"] = "fixture"


class LambdaAPIError(LambdaFixtureModel):
    code: str
    message: str
    retryable: bool = False


class LambdaAPIResponseEnvelope(LambdaFixtureModel):
    ok: bool
    data: Any | None = None
    error: LambdaAPIError | None = None
