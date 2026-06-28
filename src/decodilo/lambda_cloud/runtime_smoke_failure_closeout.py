"""Offline closeout for an M075R runtime-smoke command failure."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.runtime_smoke_failure_record import (
    load_lambda_runtime_smoke_failure_record,
)

RuntimeSmokeFailureCloseoutStatus = Literal[
    "closed_runtime_smoke_command_failed_evidence_insufficient",
    "closed_runtime_smoke_command_failed_with_artifact_metadata",
    "unresolved",
]


class LambdaRuntimeSmokeFailureCloseout(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075S"
    closeout_status: RuntimeSmokeFailureCloseoutStatus
    closeout_succeeded: bool
    infrastructure_clean: bool
    decodilo_runtime_smoke_failed: bool
    failure_evidence_insufficient: bool
    retry_requires_failure_artifact_capture: bool
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_closeout(self) -> LambdaRuntimeSmokeFailureCloseout:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M075S failure closeout must not authorize launch or spend")
        if self.closeout_succeeded and self.closeout_status == "unresolved":
            raise ValueError("unresolved closeout cannot be marked succeeded")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_runtime_smoke_failure_closeout_from_path(
    *,
    failure_record: str | Path,
) -> LambdaRuntimeSmokeFailureCloseout:
    record = load_lambda_runtime_smoke_failure_record(failure_record)
    blockers = list(record.blockers)
    infrastructure_clean = (
        record.infrastructure_passed
        and record.termination_verified
        and record.final_instance_count == 0
        and record.final_unmanaged_count == 0
    )
    if not infrastructure_clean:
        blockers.append("infrastructure_not_clean")
    decodilo_failed = record.failure_status == "runtime_smoke_command_failed"
    if not decodilo_failed:
        blockers.append("runtime_smoke_failure_not_classified")
    evidence_insufficient = (
        record.failure_diagnosis_status == "insufficient_failure_artifact_evidence"
    )
    if blockers:
        status: RuntimeSmokeFailureCloseoutStatus = "unresolved"
    elif evidence_insufficient:
        status = "closed_runtime_smoke_command_failed_evidence_insufficient"
    else:
        status = "closed_runtime_smoke_command_failed_with_artifact_metadata"
    return LambdaRuntimeSmokeFailureCloseout(
        closeout_status=status,
        closeout_succeeded=not blockers,
        infrastructure_clean=infrastructure_clean,
        decodilo_runtime_smoke_failed=decodilo_failed,
        failure_evidence_insufficient=evidence_insufficient,
        retry_requires_failure_artifact_capture=evidence_insufficient,
        historical_billable_action_performed=record.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=[
            "M075S is offline; future retry must capture the declared failure artifact",
        ],
    )


def load_lambda_runtime_smoke_failure_closeout(
    path: str | Path,
) -> LambdaRuntimeSmokeFailureCloseout:
    return LambdaRuntimeSmokeFailureCloseout.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_runtime_smoke_failure_closeout(
    path: str | Path,
    closeout: LambdaRuntimeSmokeFailureCloseout,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(closeout.to_json(), encoding="utf-8")
