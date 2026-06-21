"""M026 real-launch decision record for M027 implementation authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaRealLaunchDecisionStatus = Literal[
    "blocked",
    "needs_more_evidence",
    "approve_m027_minimal_real_mutation_implementation",
]


class LambdaRealLaunchDecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_id: str = "lambda-real-launch-decision-m026"
    status: LambdaRealLaunchDecisionStatus
    rationale: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_required_steps: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    live_mutating_operations: int = 0

    @model_validator(mode="after")
    def _disabled(self) -> LambdaRealLaunchDecisionRecord:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M026 decision record cannot enable launch or mutation")
        if self.live_mutating_operations:
            raise ValueError("M026 decision record cannot report live mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def load_lambda_real_launch_decision_record(path: str | Path) -> LambdaRealLaunchDecisionRecord:
    return LambdaRealLaunchDecisionRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_real_launch_decision_record(
    path: str | Path,
    record: LambdaRealLaunchDecisionRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
