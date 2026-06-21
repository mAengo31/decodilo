"""Minimal M027 launch/terminate request models for fake-server execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _is_fake_instance_id(value: str) -> bool:
    return value.startswith("fake-i-") or value == "planned-owned-placeholder"


class LambdaMinimalLaunchOneInstanceRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_schema_version: int = 1
    operation: Literal["launch_one_instance"] = "launch_one_instance"
    instance_type: str = Field(min_length=1)
    region: str = Field(min_length=1)
    image_id: str | None = None
    image_name: str | None = None
    ssh_key_ref: str | None = None
    filesystem_refs: list[str] = Field(default_factory=list)
    idempotency_key: str = Field(min_length=1)
    dry_run_plan_hash: str = Field(min_length=1)
    budget_lock_hash: str = Field(min_length=1)
    approval_manifest_hash: str = Field(min_length=1)
    resource_ledger_hash: str = Field(min_length=1)
    teardown_plan_hash: str = Field(min_length=1)
    fake_server_only: bool = True
    real_lambda_request_allowed: bool = False

    @model_validator(mode="after")
    def _fake_only(self) -> LambdaMinimalLaunchOneInstanceRequest:
        if not self.fake_server_only or self.real_lambda_request_allowed:
            raise ValueError("minimal launch request is fake-server-only in M027")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaMinimalTerminateOwnedInstanceRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_schema_version: int = 1
    operation: Literal["terminate_owned_instance"] = "terminate_owned_instance"
    owned_instance_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    resource_scope_hash: str = Field(min_length=1)
    ledger_hash: str = Field(min_length=1)
    termination_verification_policy_hash: str = Field(min_length=1)
    fake_server_only: bool = True
    real_lambda_request_allowed: bool = False

    @model_validator(mode="after")
    def _fake_owned_only(self) -> LambdaMinimalTerminateOwnedInstanceRequest:
        if not self.fake_server_only or self.real_lambda_request_allowed:
            raise ValueError("minimal terminate request is fake-server-only in M027")
        if not _is_fake_instance_id(self.owned_instance_id):
            raise ValueError("M027 terminate request requires owned synthetic instance id")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaMinimalMutationPreparedRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_schema_version: int = 1
    operation: Literal["launch_one_instance", "terminate_owned_instance"]
    future_http_method: str
    future_endpoint_template: str
    executable_url: str | None = None
    request_body_redacted: dict[str, Any] = Field(default_factory=dict)
    request_body_present: bool = True
    request_body_executable: bool = False
    fake_server_only: bool = True
    real_lambda_request_allowed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _review_or_fake_only(self) -> LambdaMinimalMutationPreparedRequest:
        if (
            not self.fake_server_only
            or self.real_lambda_request_allowed
            or self.request_body_executable
            or self.launch_ready
            or self.launch_allowed
            or self.real_mutation_enabled
            or self.billable_action_performed
        ):
            raise ValueError("prepared minimal request cannot enable real Lambda execution")
        if self.executable_url and "lambdalabs.com" in self.executable_url.lower():
            raise ValueError("prepared minimal request rejects real Lambda URLs")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def prepare_minimal_launch_request(
    request: LambdaMinimalLaunchOneInstanceRequest,
    *,
    fake_executable_url: str | None = (
        "memory://lambda-minimal-fake-server/instance-operations/launch"
    ),
) -> LambdaMinimalMutationPreparedRequest:
    return LambdaMinimalMutationPreparedRequest(
        operation=request.operation,
        future_http_method="POST",
        future_endpoint_template="/instance-operations/launch",
        executable_url=fake_executable_url,
        request_body_redacted={
            "region_name": request.region,
            "instance_type_name": request.instance_type,
            "ssh_key_names": ["<redacted>"] if request.ssh_key_ref else [],
            "quantity": 1,
            "image_id": "<redacted>" if request.image_id else None,
            "image_name": request.image_name,
            "file_system_names": ["<redacted>"] if request.filesystem_refs else [],
            "idempotency_key": request.idempotency_key,
            "budget_lock_hash": request.budget_lock_hash,
        },
    )


def prepare_minimal_terminate_request(
    request: LambdaMinimalTerminateOwnedInstanceRequest,
    *,
    fake_executable_url: str | None = None,
) -> LambdaMinimalMutationPreparedRequest:
    url = fake_executable_url or (
        "memory://lambda-minimal-fake-server/instance-operations/terminate"
    )
    return LambdaMinimalMutationPreparedRequest(
        operation=request.operation,
        future_http_method="POST",
        future_endpoint_template="/instance-operations/terminate",
        executable_url=url,
        request_body_redacted={
            "instance_ids": [request.owned_instance_id],
            "idempotency_key": request.idempotency_key,
            "resource_scope_hash": request.resource_scope_hash,
        },
    )


def load_lambda_minimal_prepared_request(path: str | Path) -> LambdaMinimalMutationPreparedRequest:
    return LambdaMinimalMutationPreparedRequest.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_minimal_prepared_request(
    path: str | Path,
    request: LambdaMinimalMutationPreparedRequest,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(request.to_json(), encoding="utf-8")
