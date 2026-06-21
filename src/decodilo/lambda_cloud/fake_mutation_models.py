"""Fake-only Lambda mutation-shaped request and response models."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FakeLambdaMutationOperation = Literal[
    "fake_launch_instance",
    "fake_terminate_instance",
    "fake_restart_instance",
    "fake_create_ssh_key",
    "fake_delete_ssh_key",
    "fake_create_filesystem",
    "fake_delete_filesystem",
]


def _validate_fake_id(resource_id: str, prefixes: tuple[str, ...]) -> None:
    if not resource_id.startswith(prefixes):
        raise ValueError(f"fake mutation resource id must start with one of {prefixes!r}")


class FakeLambdaMutationBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    fake_only: bool = True
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _enforce_fake_only(self) -> FakeLambdaMutationBase:
        if not self.fake_only:
            raise ValueError("fake mutation model must have fake_only=true")
        if self.real_lambda_api_used:
            raise ValueError("fake mutation model must not use real Lambda API")
        if self.billable_action_performed:
            raise ValueError("fake mutation model must not perform billable actions")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class FakeLambdaMutationRequest(FakeLambdaMutationBase):
    operation: FakeLambdaMutationOperation
    idempotency_key: str = Field(min_length=1)


class FakeLambdaLaunchRequest(FakeLambdaMutationRequest):
    operation: Literal["fake_launch_instance"] = "fake_launch_instance"
    lifecycle_id: str
    resource_index: int = Field(ge=0)
    instance_type: str
    region: str
    requested_instance_id: str | None = None

    @model_validator(mode="after")
    def _validate_requested_id(self) -> FakeLambdaLaunchRequest:
        if self.requested_instance_id is not None:
            _validate_fake_id(self.requested_instance_id, ("fake-i-",))
        return self


class FakeLambdaTerminateRequest(FakeLambdaMutationRequest):
    operation: Literal["fake_terminate_instance"] = "fake_terminate_instance"
    instance_id: str

    @model_validator(mode="after")
    def _validate_instance_id(self) -> FakeLambdaTerminateRequest:
        _validate_fake_id(self.instance_id, ("fake-i-",))
        return self


class FakeLambdaRestartRequest(FakeLambdaMutationRequest):
    operation: Literal["fake_restart_instance"] = "fake_restart_instance"
    instance_id: str

    @model_validator(mode="after")
    def _validate_instance_id(self) -> FakeLambdaRestartRequest:
        _validate_fake_id(self.instance_id, ("fake-i-",))
        return self


class FakeLambdaCreateSSHKeyRequest(FakeLambdaMutationRequest):
    operation: Literal["fake_create_ssh_key"] = "fake_create_ssh_key"
    key_name: str


class FakeLambdaDeleteSSHKeyRequest(FakeLambdaMutationRequest):
    operation: Literal["fake_delete_ssh_key"] = "fake_delete_ssh_key"
    key_id: str

    @model_validator(mode="after")
    def _validate_key_id(self) -> FakeLambdaDeleteSSHKeyRequest:
        _validate_fake_id(self.key_id, ("fake-key-",))
        return self


class FakeLambdaCreateFilesystemRequest(FakeLambdaMutationRequest):
    operation: Literal["fake_create_filesystem"] = "fake_create_filesystem"
    filesystem_name: str


class FakeLambdaDeleteFilesystemRequest(FakeLambdaMutationRequest):
    operation: Literal["fake_delete_filesystem"] = "fake_delete_filesystem"
    filesystem_id: str

    @model_validator(mode="after")
    def _validate_filesystem_id(self) -> FakeLambdaDeleteFilesystemRequest:
        _validate_fake_id(self.filesystem_id, ("fake-fs-",))
        return self


class FakeLambdaMutationResponse(FakeLambdaMutationBase):
    operation: FakeLambdaMutationOperation
    idempotency_key: str | None = None
    status: str = "ok"
    message: str = ""


class FakeLambdaLaunchResponse(FakeLambdaMutationResponse):
    operation: Literal["fake_launch_instance"] = "fake_launch_instance"
    instance_id: str
    lifecycle_state: str = "running"

    @model_validator(mode="after")
    def _validate_instance_id(self) -> FakeLambdaLaunchResponse:
        _validate_fake_id(self.instance_id, ("fake-i-",))
        return self


class FakeLambdaTerminateResponse(FakeLambdaMutationResponse):
    operation: Literal["fake_terminate_instance"] = "fake_terminate_instance"
    instance_id: str
    lifecycle_state: str = "terminated"

    @model_validator(mode="after")
    def _validate_instance_id(self) -> FakeLambdaTerminateResponse:
        _validate_fake_id(self.instance_id, ("fake-i-",))
        return self


class FakeLambdaRestartResponse(FakeLambdaMutationResponse):
    operation: Literal["fake_restart_instance"] = "fake_restart_instance"
    instance_id: str
    lifecycle_state: str = "running"

    @model_validator(mode="after")
    def _validate_instance_id(self) -> FakeLambdaRestartResponse:
        _validate_fake_id(self.instance_id, ("fake-i-",))
        return self


class FakeLambdaCreateSSHKeyResponse(FakeLambdaMutationResponse):
    operation: Literal["fake_create_ssh_key"] = "fake_create_ssh_key"
    key_id: str

    @model_validator(mode="after")
    def _validate_key_id(self) -> FakeLambdaCreateSSHKeyResponse:
        _validate_fake_id(self.key_id, ("fake-key-",))
        return self


class FakeLambdaDeleteSSHKeyResponse(FakeLambdaMutationResponse):
    operation: Literal["fake_delete_ssh_key"] = "fake_delete_ssh_key"
    key_id: str
    lifecycle_state: str = "deleted"

    @model_validator(mode="after")
    def _validate_key_id(self) -> FakeLambdaDeleteSSHKeyResponse:
        _validate_fake_id(self.key_id, ("fake-key-",))
        return self


class FakeLambdaCreateFilesystemResponse(FakeLambdaMutationResponse):
    operation: Literal["fake_create_filesystem"] = "fake_create_filesystem"
    filesystem_id: str

    @model_validator(mode="after")
    def _validate_filesystem_id(self) -> FakeLambdaCreateFilesystemResponse:
        _validate_fake_id(self.filesystem_id, ("fake-fs-",))
        return self


class FakeLambdaDeleteFilesystemResponse(FakeLambdaMutationResponse):
    operation: Literal["fake_delete_filesystem"] = "fake_delete_filesystem"
    filesystem_id: str
    lifecycle_state: str = "deleted"

    @model_validator(mode="after")
    def _validate_filesystem_id(self) -> FakeLambdaDeleteFilesystemResponse:
        _validate_fake_id(self.filesystem_id, ("fake-fs-",))
        return self
