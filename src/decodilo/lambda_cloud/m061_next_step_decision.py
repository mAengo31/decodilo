"""M061 next-step decision after M060 hostname identity closeout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_hostname_identity_closeout import (
    load_lambda_ssh_hostname_identity_closeout,
)

LambdaM061NextStepDecisionStatus = Literal[
    "plan_whoami_identity_command_review",
    "pause_remote_command_progression",
    "needs_more_evidence",
]

_FORBIDDEN_STATUSES = {
    "whoami_now",
    "run_command_now",
    "launch_now",
    "nvidia_smi_now",
    "python_now",
    "training_now",
    "launch_allowed",
    "launch_ready",
}


class LambdaM061NextStepDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_status: LambdaM061NextStepDecisionStatus
    next_allowed_review_command: str | None = None
    command_authorized_now: bool = False
    launch_authorized_now: bool = False
    gpu_visibility_authorized_now: bool = False
    python_authorized_now: bool = False
    training_authorized_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaM061NextStepDecision:
        if self.decision_status in _FORBIDDEN_STATUSES:
            raise ValueError("forbidden M061 decision status")
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.command_authorized_now
            or self.launch_authorized_now
            or self.gpu_visibility_authorized_now
            or self.python_authorized_now
            or self.training_authorized_now
        ):
            raise ValueError("M061 decision cannot authorize immediate execution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m061_next_step_decision_from_paths(
    *,
    hostname_closeout: str | Path,
) -> LambdaM061NextStepDecision:
    closeout = load_lambda_ssh_hostname_identity_closeout(hostname_closeout)
    blockers = list(closeout.blockers)
    if closeout.closeout_succeeded and closeout.command == "hostname":
        decision: LambdaM061NextStepDecisionStatus = "plan_whoami_identity_command_review"
        next_command = "whoami"
    elif blockers:
        decision = "needs_more_evidence"
        next_command = None
    else:
        decision = "pause_remote_command_progression"
        next_command = None
    return LambdaM061NextStepDecision(
        decision_status=decision,
        next_allowed_review_command=next_command,
        blockers=sorted(set(blockers)),
        warnings=[
            "M061 decision authorizes planning only",
            "whoami, launch, GPU visibility, Python, and training remain unauthorized now",
        ],
    )


def load_lambda_m061_next_step_decision(path: str | Path) -> LambdaM061NextStepDecision:
    return LambdaM061NextStepDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m061_next_step_decision(
    path: str | Path,
    report: LambdaM061NextStepDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
