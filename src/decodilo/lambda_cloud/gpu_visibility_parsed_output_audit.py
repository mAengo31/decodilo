"""Audit whether M063 preserved structured GPU visibility output fields."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from decodilo.lambda_cloud.gpu_visibility_output_policy import (
    load_lambda_gpu_visibility_output_policy,
)
from decodilo.lambda_cloud.gpu_visibility_success_record import (
    load_lambda_gpu_visibility_success_record,
)

LambdaGPUVisibilityParsedOutputAuditStatus = Literal[
    "parsed_fields_present",
    "output_hash_only",
    "missing_output",
]

LambdaGPUVisibilityParsedOutputRecommendedAction = Literal[
    "accept_full_gpu_visibility_closeout",
    "accept_hash_only_with_warning",
    "rerun_future_query_with_parsed_field_capture",
]


class LambdaGPUVisibilityParsedOutputAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    parsed_output_audit_status: LambdaGPUVisibilityParsedOutputAuditStatus
    gpu_name_present: bool
    memory_total_present: bool
    driver_version_present: bool
    stdout_hash_prefix: str | None = None
    raw_stdout_reported: bool = False
    recommended_action: LambdaGPUVisibilityParsedOutputRecommendedAction
    warnings: list[str] = []
    blockers: list[str] = []
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaGPUVisibilityParsedOutputAudit:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M064 parsed output audit cannot enable launch or mutation")
        if self.raw_stdout_reported:
            raise ValueError("M064 parsed output audit cannot accept raw stdout")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_gpu_visibility_parsed_output_audit_from_paths(
    *,
    success_record: str | Path,
    output_policy: str | Path,
) -> LambdaGPUVisibilityParsedOutputAudit:
    success = load_lambda_gpu_visibility_success_record(success_record)
    policy = load_lambda_gpu_visibility_output_policy(output_policy)
    blockers = [*policy.blockers]
    gpu_name_present = bool(success.parsed_gpu_name)
    memory_total_present = bool(success.parsed_memory_total)
    driver_version_present = bool(success.parsed_driver_version)
    if success.raw_stdout_reported:
        blockers.append("raw_stdout_reported")
    if gpu_name_present and memory_total_present and driver_version_present:
        status: LambdaGPUVisibilityParsedOutputAuditStatus = "parsed_fields_present"
        action: LambdaGPUVisibilityParsedOutputRecommendedAction = (
            "accept_full_gpu_visibility_closeout"
        )
        warnings: list[str] = []
    elif success.stdout_hash_prefix:
        status = "output_hash_only"
        action = "accept_hash_only_with_warning"
        warnings = [
            "M063 output was preserved as a redacted hash only; parsed GPU fields are absent"
        ]
    else:
        status = "missing_output"
        action = "rerun_future_query_with_parsed_field_capture"
        blockers.append("gpu_visibility_output_missing")
        warnings = []
    return LambdaGPUVisibilityParsedOutputAudit(
        parsed_output_audit_status=status,
        gpu_name_present=gpu_name_present,
        memory_total_present=memory_total_present,
        driver_version_present=driver_version_present,
        stdout_hash_prefix=success.stdout_hash_prefix,
        raw_stdout_reported=success.raw_stdout_reported,
        recommended_action=action,
        warnings=warnings,
        blockers=sorted(set(blockers)),
    )


def load_lambda_gpu_visibility_parsed_output_audit(
    path: str | Path,
) -> LambdaGPUVisibilityParsedOutputAudit:
    return LambdaGPUVisibilityParsedOutputAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_gpu_visibility_parsed_output_audit(
    path: str | Path,
    report: LambdaGPUVisibilityParsedOutputAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
