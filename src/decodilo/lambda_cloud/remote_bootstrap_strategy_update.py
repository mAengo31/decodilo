"""Remote bootstrap strategy update after M051B metadata-only success."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.metadata_bootstrap_closeout import (
    load_lambda_metadata_bootstrap_closeout,
)

LambdaRemoteBootstrapRecommendedNextStage = Literal[
    "ssh_connectivity_planning",
    "stay_metadata_only",
    "pause_remote_execution",
    "needs_more_evidence",
]


class LambdaRemoteBootstrapStrategyUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    metadata_bootstrap_successful: bool
    next_options: list[str] = Field(default_factory=list)
    recommended_next_stage: LambdaRemoteBootstrapRecommendedNextStage
    training_approved: bool = False
    ssh_approved_now: bool = False
    remote_commands_approved_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaRemoteBootstrapStrategyUpdate:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.training_approved
            or self.ssh_approved_now
            or self.remote_commands_approved_now
        ):
            raise ValueError("strategy update cannot approve immediate remote execution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remote_bootstrap_strategy_update_from_paths(
    *,
    metadata_closeout: str | Path,
) -> LambdaRemoteBootstrapStrategyUpdate:
    closeout = load_lambda_metadata_bootstrap_closeout(metadata_closeout)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.extend(closeout.blockers or ["metadata_bootstrap_closeout_not_succeeded"])
    success = not blockers
    return LambdaRemoteBootstrapStrategyUpdate(
        metadata_bootstrap_successful=success,
        next_options=[
            "approve_future_ssh_connectivity_only_review",
            "repeat_metadata_bootstrap_not_needed",
            "pause_remote_execution",
        ],
        recommended_next_stage=(
            "ssh_connectivity_planning" if success else "needs_more_evidence"
        ),
        blockers=sorted(set(blockers)),
        warnings=[
            "training remains not approved",
            "SSH connectivity planning is not SSH execution",
        ],
    )


def load_lambda_remote_bootstrap_strategy_update(
    path: str | Path,
) -> LambdaRemoteBootstrapStrategyUpdate:
    return LambdaRemoteBootstrapStrategyUpdate.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_bootstrap_strategy_update(
    path: str | Path,
    report: LambdaRemoteBootstrapStrategyUpdate,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
