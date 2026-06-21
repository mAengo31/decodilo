"""Strand-AI lambda-cli response shape models and parsers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrandLaunchData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    instance_ids: list[str] = Field(min_length=1)


class StrandLaunchResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    data: StrandLaunchData


class StrandTerminateResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    data: dict[str, Any] | None = None


class StrandErrorDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    message: str = Field(min_length=1)


class StrandErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    error: StrandErrorDetail


class StrandInstanceListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    data: list[dict[str, Any]]


class StrandInstanceTypeResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    data: dict[str, Any]


def parse_strand_launch_instance_id(payload: dict[str, Any]) -> str:
    response = StrandLaunchResponse.model_validate(payload)
    instance_id = response.data.instance_ids[0]
    if not instance_id:
        raise ValueError("Strand launch response returned empty instance id")
    return instance_id


def parse_strand_terminate_success(
    *,
    status_code: int,
    payload: dict[str, Any] | None = None,
) -> bool:
    del payload
    return 200 <= status_code < 300


def parse_strand_error_message(payload: dict[str, Any]) -> str:
    return StrandErrorResponse.model_validate(payload).error.message
