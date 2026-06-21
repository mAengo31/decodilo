"""Combined report for the disabled Lambda real mutation skeleton."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.disabled_real_mutation_transport import (
    LambdaRealMutationDisabledReport,
)
from decodilo.lambda_cloud.real_mutation_execution_guard import (
    LambdaRealMutationExecutionGuardReport,
)
from decodilo.lambda_cloud.real_mutation_request_builder import (
    LambdaRealMutationRequestBuildResult,
)


class LambdaRealMutationSkeletonReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    skeleton_present: bool = True
    disabled_transport_report: LambdaRealMutationDisabledReport | None = None
    request_build_result: LambdaRealMutationRequestBuildResult | None = None
    execution_guard_report: LambdaRealMutationExecutionGuardReport | None = None
    skeleton_status: str = "disabled"
    real_lambda_api_used: bool = False
    real_mutating_operations: int = 0
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def load_lambda_real_mutation_skeleton_report(
    path: str | Path,
) -> LambdaRealMutationSkeletonReport:
    return LambdaRealMutationSkeletonReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_real_mutation_skeleton_report(
    path: str | Path,
    report: LambdaRealMutationSkeletonReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
