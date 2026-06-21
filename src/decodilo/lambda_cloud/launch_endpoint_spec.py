"""Review-only launch and termination endpoint specifications."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

LambdaEndpointSpecSource = Literal[
    "operator_provided",
    "docs_observed",
    "fixture",
    "unofficial_cli_behavior",
    "unknown",
]
LambdaEndpointSpecConfidence = Literal["unknown", "low", "medium", "high"]


class LambdaEndpointOperationSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation: Literal["launch_one_instance", "terminate_owned_instance"]
    method: str
    path_template: str
    source: LambdaEndpointSpecSource = "unknown"
    source_url: str | None = None
    source_timestamp: str | None = None
    request_schema_summary: str | None = None
    response_schema_summary: str | None = None
    confidence: LambdaEndpointSpecConfidence = "unknown"
    verified_for_real_mutation: bool = False
    notes: str | None = None
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaEndpointOperationSpec:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("endpoint spec cannot enable launch")
        if not self.method:
            raise ValueError("endpoint spec requires method")
        if not self.path_template:
            raise ValueError("endpoint spec requires path template")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaLaunchEndpointSpec(LambdaEndpointOperationSpec):
    operation: Literal["launch_one_instance"] = "launch_one_instance"


class LambdaTerminateEndpointSpec(LambdaEndpointOperationSpec):
    operation: Literal["terminate_owned_instance"] = "terminate_owned_instance"


def build_lambda_endpoint_spec(
    *,
    operation: str,
    method: str,
    path_template: str,
    source: LambdaEndpointSpecSource = "operator_provided",
    source_url: str | None = None,
    source_timestamp: str | None = None,
    request_schema_summary: str | None = None,
    response_schema_summary: str | None = None,
    confidence: LambdaEndpointSpecConfidence = "medium",
    notes: str | None = None,
) -> LambdaEndpointOperationSpec:
    payload = {
        "method": method.upper(),
        "path_template": path_template,
        "source": source,
        "source_url": source_url,
        "source_timestamp": source_timestamp,
        "request_schema_summary": request_schema_summary,
        "response_schema_summary": response_schema_summary,
        "confidence": confidence,
        "verified_for_real_mutation": confidence in {"medium", "high"},
        "notes": notes,
    }
    if operation == "launch_one_instance":
        return LambdaLaunchEndpointSpec(**payload)
    if operation == "terminate_owned_instance":
        return LambdaTerminateEndpointSpec(**payload)
    raise ValueError(f"unsupported endpoint operation: {operation}")


def load_lambda_endpoint_spec(path: str | Path) -> LambdaEndpointOperationSpec:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    operation = data.get("operation")
    if operation == "launch_one_instance":
        return LambdaLaunchEndpointSpec.model_validate(data)
    if operation == "terminate_owned_instance":
        return LambdaTerminateEndpointSpec.model_validate(data)
    raise ValueError(f"unsupported endpoint operation: {operation}")


def write_lambda_endpoint_spec(path: str | Path, spec: LambdaEndpointOperationSpec) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(spec.to_json(), encoding="utf-8")
