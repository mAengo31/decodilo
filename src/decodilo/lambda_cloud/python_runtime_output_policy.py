"""Future-only output policy for the M065 Python version query."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaPythonRuntimeOutputPolicyStatus = Literal[
    "python_runtime_output_policy_defined_future_only",
    "blocked",
]


class LambdaPythonRuntimeOutputPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    output_policy_status: LambdaPythonRuntimeOutputPolicyStatus
    stdout_capture_allowed_future_only: bool = True
    stderr_capture_allowed_future_only: bool = True
    max_stdout_bytes: int = 1024
    max_stderr_bytes: int = 2048
    expected_output: str = "python_version_string"
    expected_stdout_regex: str = r"^Python \d+\.\d+(\.\d+)?"
    environment_variable_capture_allowed: bool = False
    filesystem_path_capture_allowed: bool = False
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
    def _validate_future_only(self) -> LambdaPythonRuntimeOutputPolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.environment_variable_capture_allowed
            or self.filesystem_path_capture_allowed
            or self.raw_unbounded_output_allowed
            or self.private_key_material_allowed
            or not self.secret_redaction_required
        ):
            raise ValueError("Python runtime output policy cannot enable execution")
        if self.max_stdout_bytes <= 0 or self.max_stdout_bytes > 1024:
            raise ValueError("M065 stdout capture must be bounded to 1024 bytes or less")
        if self.max_stderr_bytes <= 0 or self.max_stderr_bytes > 2048:
            raise ValueError("M065 stderr capture must be bounded to 2048 bytes or less")
        re.compile(self.expected_stdout_regex)
        for pattern in self.redaction_patterns:
            re.compile(pattern)
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_python_runtime_output_policy() -> LambdaPythonRuntimeOutputPolicy:
    return LambdaPythonRuntimeOutputPolicy(
        output_policy_status="python_runtime_output_policy_defined_future_only",
        warnings=[
            "M064 permits only future bounded Python version stdout/stderr capture",
            (
                "Environment variables, filesystem paths, private key material, "
                "and secrets remain forbidden"
            ),
        ],
    )


def load_lambda_python_runtime_output_policy(
    path: str | Path,
) -> LambdaPythonRuntimeOutputPolicy:
    return LambdaPythonRuntimeOutputPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_python_runtime_output_policy(
    path: str | Path,
    report: LambdaPythonRuntimeOutputPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
