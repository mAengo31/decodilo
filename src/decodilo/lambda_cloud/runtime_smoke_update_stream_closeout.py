"""M075U closeout for runtime-smoke update-stream timeout failures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.runtime_smoke_update_stream_failure_record import (
    load_lambda_runtime_smoke_update_stream_failure_record,
)

RuntimeSmokeUpdateStreamCloseoutStatus = Literal[
    "closed_runtime_smoke_update_stream_timeout",
    "blocked",
]


class LambdaRuntimeSmokeUpdateStreamCloseout(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075U"
    closeout_status: RuntimeSmokeUpdateStreamCloseoutStatus
    closeout_succeeded: bool
    retry_requires_local_update_stream_fix: bool = True
    infrastructure_passed: bool
    update_stream_failure_classified: bool
    artifact_body_or_summary_available: bool
    termination_verified: bool
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_closeout(self) -> LambdaRuntimeSmokeUpdateStreamCloseout:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M075U closeout must remain offline")
        if self.closeout_succeeded and self.blockers:
            raise ValueError("successful M075U closeout cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_runtime_smoke_update_stream_closeout_from_path(
    *,
    failure_record: str | Path,
) -> LambdaRuntimeSmokeUpdateStreamCloseout:
    record = load_lambda_runtime_smoke_update_stream_failure_record(failure_record)
    blockers: list[str] = []
    classified = record.failure_status == "runtime_smoke_update_stream_failed"
    artifact_available = record.artifact_body_persisted or record.parsed_summary_persisted
    if not classified:
        blockers.append("update_stream_failure_not_classified")
    if not record.infrastructure_passed:
        blockers.append("infrastructure_not_passed")
    if not artifact_available:
        blockers.append("artifact_body_or_summary_missing")
    if not record.termination_verified:
        blockers.append("termination_not_verified")
    if record.final_instance_count != 0 or record.final_unmanaged_count != 0:
        blockers.append("final_discovery_not_clean")
    return LambdaRuntimeSmokeUpdateStreamCloseout(
        closeout_status=(
            "closed_runtime_smoke_update_stream_timeout" if not blockers else "blocked"
        ),
        closeout_succeeded=not blockers,
        infrastructure_passed=record.infrastructure_passed,
        update_stream_failure_classified=classified,
        artifact_body_or_summary_available=artifact_available,
        termination_verified=record.termination_verified,
        final_instance_count=record.final_instance_count,
        final_unmanaged_count=record.final_unmanaged_count,
        historical_billable_action_performed=record.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=[
            "M075R3 cleanup is closed; retry requires local update-stream fix first",
        ],
    )


def load_lambda_runtime_smoke_update_stream_closeout(
    path: str | Path,
) -> LambdaRuntimeSmokeUpdateStreamCloseout:
    return LambdaRuntimeSmokeUpdateStreamCloseout.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_runtime_smoke_update_stream_closeout(
    path: str | Path,
    closeout: LambdaRuntimeSmokeUpdateStreamCloseout,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(closeout.to_json(), encoding="utf-8")
