"""M028 final execution approval package for future M029 only."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m028_decision_record import LambdaM028DecisionRecord
from decodilo.lambda_cloud.m029_launch_authorization import LambdaM029AuthorizationPackage


class LambdaFinalExecutionApproval(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    approval_id: str = "lambda-final-execution-approval-m028"
    decision_record: LambdaM028DecisionRecord
    m029_authorization: LambdaM029AuthorizationPackage
    approval_status: str
    approved_for_next_milestone_only: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaFinalExecutionApproval:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M028 final approval cannot enable launch or mutation")
        if not self.approved_for_next_milestone_only:
            raise ValueError("M028 approval must be next-milestone-only")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_final_execution_approval(
    *,
    decision_record: LambdaM028DecisionRecord,
    m029_authorization: LambdaM029AuthorizationPackage,
) -> LambdaFinalExecutionApproval:
    blockers = [*decision_record.blockers, *m029_authorization.blockers]
    return LambdaFinalExecutionApproval(
        decision_record=decision_record,
        m029_authorization=m029_authorization,
        approval_status=decision_record.status,
        blockers=blockers,
        warnings=[
            "Approval is for future M029 authorization only; M028 execution is disabled."
        ],
    )


def write_lambda_final_execution_approval(
    path: str | Path,
    approval: LambdaFinalExecutionApproval,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(approval.to_json(), encoding="utf-8")

