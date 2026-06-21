"""M053 next-step decision after M052 metadata bootstrap closeout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.metadata_bootstrap_closeout import (
    load_lambda_metadata_bootstrap_closeout,
)
from decodilo.lambda_cloud.remote_bootstrap_strategy_update import (
    load_lambda_remote_bootstrap_strategy_update,
)

LambdaM053NextStepDecisionStatus = Literal[
    "plan_ssh_connectivity_only_review",
    "stay_metadata_only_no_next_remote_access",
    "pause_remote_runtime_work",
    "needs_more_evidence",
]

_FORBIDDEN_STATUSES = {
    "ssh_now",
    "run_command_now",
    "launch_now",
    "training_now",
    "launch_allowed",
    "launch_ready",
}


class LambdaM053NextStepDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_status: LambdaM053NextStepDecisionStatus
    ssh_authorized_now: bool = False
    remote_commands_authorized_now: bool = False
    launch_authorized_now: bool = False
    training_authorized_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaM053NextStepDecision:
        if self.decision_status in _FORBIDDEN_STATUSES:
            raise ValueError("forbidden M053 decision status")
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.ssh_authorized_now
            or self.remote_commands_authorized_now
            or self.launch_authorized_now
            or self.training_authorized_now
        ):
            raise ValueError("M053 decision cannot authorize immediate execution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m053_next_step_decision_from_paths(
    *,
    metadata_closeout: str | Path,
    strategy_update: str | Path,
) -> LambdaM053NextStepDecision:
    closeout = load_lambda_metadata_bootstrap_closeout(metadata_closeout)
    strategy = load_lambda_remote_bootstrap_strategy_update(strategy_update)
    blockers: list[str] = [*closeout.blockers, *strategy.blockers]
    if closeout.closeout_succeeded and strategy.metadata_bootstrap_successful:
        decision: LambdaM053NextStepDecisionStatus = "plan_ssh_connectivity_only_review"
    elif blockers:
        decision = "needs_more_evidence"
    else:
        decision = "stay_metadata_only_no_next_remote_access"
    return LambdaM053NextStepDecision(
        decision_status=decision,
        blockers=sorted(set(blockers)),
        warnings=[
            "M053 decision authorizes planning only",
            "SSH, commands, launch, and training remain unauthorized now",
        ],
    )


def load_lambda_m053_next_step_decision(path: str | Path) -> LambdaM053NextStepDecision:
    return LambdaM053NextStepDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m053_next_step_decision(
    path: str | Path,
    report: LambdaM053NextStepDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
