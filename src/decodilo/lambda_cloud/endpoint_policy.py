"""Endpoint policy for Lambda read-only discovery."""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict


class LambdaEndpoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation: str
    method: str
    path: str


class LambdaEndpointPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    endpoint: LambdaEndpoint
    allowed: bool
    reason: str
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaEndpointPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_schema_version: int = 1
    allow_non_get: bool = False
    mode: Literal["read_only", "m029_first_launch"] = "read_only"

    def check(self, endpoint: LambdaEndpoint) -> LambdaEndpointPolicyReport:
        method = endpoint.method.upper()
        normalized = normalize_lambda_path(endpoint.path)
        if method != "GET":
            if self.mode == "m029_first_launch":
                return self._check_m029_mutation(endpoint, method, normalized)
            return LambdaEndpointPolicyReport(
                endpoint=endpoint,
                allowed=False,
                reason="non-GET Lambda endpoint denied",
            )
        if endpoint.operation not in _READ_OPERATION_PATHS:
            return LambdaEndpointPolicyReport(
                endpoint=endpoint,
                allowed=False,
                reason="unknown Lambda operation denied",
            )
        expected = _READ_OPERATION_PATHS[endpoint.operation]
        if expected.endswith("/{instance_id}"):
            pattern = "^" + re.escape(expected[:-14]) + r"/[^/]+$"
            allowed = bool(re.match(pattern, normalized))
        else:
            allowed = normalized == expected
        return LambdaEndpointPolicyReport(
            endpoint=endpoint,
            allowed=allowed,
            reason="read-only endpoint allowlisted" if allowed else "endpoint path mismatch",
        )

    def _check_m029_mutation(
        self,
        endpoint: LambdaEndpoint,
        method: str,
        normalized: str,
    ) -> LambdaEndpointPolicyReport:
        expected = _M029_OPERATION_PATHS.get(endpoint.operation)
        allowed = (
            self.allow_non_get
            and expected is not None
            and method == expected[0]
            and normalized == expected[1]
        )
        return LambdaEndpointPolicyReport(
            endpoint=endpoint,
            allowed=allowed,
            reason=(
                "M029 one-instance mutation endpoint allowlisted"
                if allowed
                else "M029 mutation endpoint denied"
            ),
        )


_READ_OPERATION_PATHS: dict[str, str] = {
    "list_instance_types": "/instance-types",
    "list_regions": "/regions",
    "list_images": "/images",
    "list_ssh_keys": "/ssh-keys",
    "list_filesystems": "/file-systems",
    "list_instances": "/instances",
    "get_instance": "/instances/{instance_id}",
    "get_quota": "/quota",
    "get_usage_estimate": "/usage",
}

_M029_OPERATION_PATHS: dict[str, tuple[str, str]] = {
    "launch_one_instance": ("POST", "/instance-operations/launch"),
    "terminate_owned_instance": ("POST", "/instance-operations/terminate"),
}


def m029_endpoint_for_operation(operation: str) -> LambdaEndpoint:
    if operation not in _M029_OPERATION_PATHS:
        raise ValueError("operation is not in the M029 mutation allowlist")
    method, path = _M029_OPERATION_PATHS[operation]
    return LambdaEndpoint(operation=operation, method=method, path=path)


def endpoint_for_operation(operation: str, *, instance_id: str | None = None) -> LambdaEndpoint:
    if operation == "get_instance":
        if not instance_id:
            raise ValueError("instance_id is required for get_instance")
        path = f"/instances/{instance_id}"
    else:
        path = _READ_OPERATION_PATHS[operation]
    return LambdaEndpoint(operation=operation, method="GET", path=path)


def normalize_lambda_path(path: str) -> str:
    normalized = "/" + path.lstrip("/")
    if normalized.startswith("/api/v1/"):
        normalized = normalized[len("/api/v1") :]
    return normalized.rstrip("/") or "/"
