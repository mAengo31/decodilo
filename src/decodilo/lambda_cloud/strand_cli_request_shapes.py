"""Strand-AI lambda-cli request shape models and validators."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrandListInstanceTypesRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: Literal["GET"] = "GET"
    path: Literal["/instance-types"] = "/instance-types"


class StrandListInstancesRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: Literal["GET"] = "GET"
    path: Literal["/instances"] = "/instances"


class StrandGetInstanceRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: Literal["GET"] = "GET"
    path: Literal["/instances/{instance_id}"] = "/instances/{instance_id}"
    instance_id: str = Field(min_length=1)


class StrandLaunchRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    region_name: str = Field(min_length=1)
    instance_type_name: str = Field(min_length=1)
    ssh_key_names: list[str] = Field(min_length=1)
    quantity: Literal[1] = 1
    name: str | None = None
    file_system_names: list[str] | None = None

    @model_validator(mode="after")
    def _validate_no_empty_names(self) -> StrandLaunchRequest:
        if any(not item for item in self.ssh_key_names):
            raise ValueError("ssh_key_names must contain existing SSH key names")
        if self.file_system_names is not None and any(
            not item for item in self.file_system_names
        ):
            raise ValueError("file_system_names cannot contain empty names")
        return self


class StrandTerminateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    instance_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_instance_ids(self) -> StrandTerminateRequest:
        if len(self.instance_ids) != 1:
            raise ValueError("M036R terminate compatibility requires exactly one instance id")
        if not self.instance_ids[0]:
            raise ValueError("instance_ids cannot contain empty values")
        return self


class StrandRequestShapeSmokeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    launch_request_valid: bool
    terminate_request_valid: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> StrandRequestShapeSmokeReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("Strand request smoke report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_strand_launch_payload(
    *,
    region_name: str,
    instance_type_name: str,
    ssh_key_name: str,
    name: str | None = None,
    file_system_names: list[str] | None = None,
) -> dict[str, object]:
    request = StrandLaunchRequest(
        region_name=region_name,
        instance_type_name=instance_type_name,
        ssh_key_names=[ssh_key_name],
        quantity=1,
        name=name,
        file_system_names=file_system_names,
    )
    payload = request.model_dump(mode="json", exclude_none=True)
    if payload.get("file_system_names") == []:
        payload.pop("file_system_names")
    return payload


def build_strand_terminate_payload(instance_id: str) -> dict[str, object]:
    return StrandTerminateRequest(instance_ids=[instance_id]).model_dump(mode="json")


def validate_strand_launch_payload(payload: dict[str, object]) -> StrandLaunchRequest:
    return StrandLaunchRequest.model_validate(payload)


def validate_strand_terminate_payload(payload: dict[str, object]) -> StrandTerminateRequest:
    return StrandTerminateRequest.model_validate(payload)


def build_strand_request_shape_smoke_report() -> StrandRequestShapeSmokeReport:
    blockers: list[str] = []
    try:
        validate_strand_launch_payload(
            build_strand_launch_payload(
                region_name="us-west-1",
                instance_type_name="gpu_1x_h100_pcie",
                ssh_key_name="existing-ssh-key",
            )
        )
        launch_valid = True
    except Exception as exc:  # noqa: BLE001
        launch_valid = False
        blockers.append(f"launch_request_invalid:{type(exc).__name__}")
    try:
        validate_strand_terminate_payload(build_strand_terminate_payload("i-123"))
        terminate_valid = True
    except Exception as exc:  # noqa: BLE001
        terminate_valid = False
        blockers.append(f"terminate_request_invalid:{type(exc).__name__}")
    return StrandRequestShapeSmokeReport(
        launch_request_valid=launch_valid,
        terminate_request_valid=terminate_valid,
        blockers=blockers,
        warnings=["Strand request smoke uses offline fixtures only"],
    )


def write_strand_request_shape_smoke_report(
    path: str | Path,
    report: StrandRequestShapeSmokeReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
