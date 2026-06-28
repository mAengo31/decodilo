"""Output capture policy for the future M063 GPU visibility query."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaGPUVisibilityOutputPolicyStatus = Literal[
    "gpu_visibility_output_policy_defined_future_only",
    "blocked",
]


class LambdaGPUVisibilityOutputPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    output_policy_status: LambdaGPUVisibilityOutputPolicyStatus
    stdout_capture_allowed_future_only: bool = True
    stderr_capture_allowed_future_only: bool = True
    max_stdout_bytes: int = 4096
    max_stderr_bytes: int = 4096
    expected_format: str = "csv_noheader"
    allowed_fields: list[str] = Field(
        default_factory=lambda: ["name", "memory.total", "driver_version"]
    )
    command_output_allowed_now: bool = False
    raw_unbounded_output_allowed: bool = False
    private_key_material_allowed: bool = False
    secret_redaction_required: bool = True
    redaction_patterns: list[str] = Field(
        default_factory=lambda: [
            r"Authorization\s*:",
            r"Bearer\s+[A-Za-z0-9._~+/=-]{8,}",
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
            r"LAMBDA_API_KEY\s*=",
            r"password\s*[=:]\s*[^\s,}\]]+",
        ]
    )
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaGPUVisibilityOutputPolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.command_output_allowed_now
            or self.raw_unbounded_output_allowed
            or self.private_key_material_allowed
            or not self.secret_redaction_required
        ):
            raise ValueError("GPU visibility output policy cannot enable execution")
        if self.max_stdout_bytes <= 0 or self.max_stdout_bytes > 4096:
            raise ValueError("M063 stdout capture must be bounded to 4096 bytes or less")
        if self.max_stderr_bytes <= 0 or self.max_stderr_bytes > 4096:
            raise ValueError("M063 stderr capture must be bounded to 4096 bytes or less")
        if self.expected_format != "csv_noheader":
            raise ValueError("M063 GPU visibility output must use csv_noheader")
        if self.allowed_fields != ["name", "memory.total", "driver_version"]:
            raise ValueError("M063 GPU visibility output fields are fixed")
        for pattern in self.redaction_patterns:
            re.compile(pattern)
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_gpu_visibility_output_policy() -> LambdaGPUVisibilityOutputPolicy:
    return LambdaGPUVisibilityOutputPolicy(
        output_policy_status="gpu_visibility_output_policy_defined_future_only",
        warnings=[
            "M062 permits only a future bounded M063 stdout/stderr capture",
            "Private key material and secrets must never appear in command output artifacts",
        ],
    )


def load_lambda_gpu_visibility_output_policy(
    path: str | Path,
) -> LambdaGPUVisibilityOutputPolicy:
    return LambdaGPUVisibilityOutputPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_gpu_visibility_output_policy(
    path: str | Path,
    report: LambdaGPUVisibilityOutputPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
