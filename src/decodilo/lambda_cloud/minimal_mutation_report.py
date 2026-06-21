"""Combined M027 minimal mutation report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.fake_server_launch_terminate_flow import (
    LambdaFakeServerLaunchTerminateFlowReport,
)
from decodilo.lambda_cloud.minimal_mutation_audit import LambdaMinimalMutationAuditReport
from decodilo.lambda_cloud.minimal_mutation_preflight import (
    LambdaMinimalMutationPreflightReport,
)


class LambdaMinimalMutationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_id: str = "lambda-minimal-mutation-m027"
    preflight: LambdaMinimalMutationPreflightReport | None = None
    fake_flow: LambdaFakeServerLaunchTerminateFlowReport | None = None
    audit: LambdaMinimalMutationAuditReport | None = None
    fake_server_execution_only: bool = True
    real_lambda_api_used: bool = False
    real_mutating_operations: int = 0
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def write_lambda_minimal_mutation_report(
    path: str | Path,
    report: LambdaMinimalMutationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
