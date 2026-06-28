"""Future next bounded synthetic Decodilo experiment readiness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.synthetic_experiment_closeout import (
    load_lambda_synthetic_experiment_closeout,
)

LambdaNextSyntheticExperimentReadinessStatus = Literal[
    "ready_for_future_next_synthetic_experiment_planning",
    "not_ready",
]


class LambdaNextSyntheticExperimentReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M078"
    readiness_status: LambdaNextSyntheticExperimentReadinessStatus
    cloud_lifecycle_ready: bool
    ssh_ready: bool
    source_bundle_ready: bool
    dependency_bundle_ready: bool
    local_only_dependency_install_ready: bool
    decodilo_cli_ready: bool
    runtime_protocol_smoke_ready: bool
    first_remote_synthetic_experiment_ready: bool
    next_experiment_must_remain_bounded_and_synthetic: bool = True
    may_move_one_step_closer_to_learner_syncer_or_diloco_shape: bool = True
    one_instance_default: bool = True
    no_model_or_data_download: bool = True
    no_internet_package_install: bool = True
    no_real_training: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_readiness(self) -> LambdaNextSyntheticExperimentReadiness:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("next synthetic experiment readiness must remain offline")
        if (
            self.readiness_status
            == "ready_for_future_next_synthetic_experiment_planning"
            and self.blockers
        ):
            raise ValueError("ready next synthetic readiness cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_next_synthetic_experiment_readiness_from_path(
    *,
    synthetic_experiment_closeout: str | Path,
) -> LambdaNextSyntheticExperimentReadiness:
    closeout = load_lambda_synthetic_experiment_closeout(synthetic_experiment_closeout)
    ready = closeout.closeout_succeeded and closeout.synthetic_experiment_success
    blockers = [] if ready else ["synthetic_experiment_closeout_not_succeeded"]
    return LambdaNextSyntheticExperimentReadiness(
        readiness_status=(
            "ready_for_future_next_synthetic_experiment_planning"
            if ready
            else "not_ready"
        ),
        cloud_lifecycle_ready=ready,
        ssh_ready=ready,
        source_bundle_ready=ready,
        dependency_bundle_ready=ready,
        local_only_dependency_install_ready=ready,
        decodilo_cli_ready=ready,
        runtime_protocol_smoke_ready=ready,
        first_remote_synthetic_experiment_ready=ready,
        blockers=blockers,
        warnings=[
            "readiness is planning-only and does not authorize launch",
            "next experiment must remain bounded, synthetic, offline, and no-training",
        ],
    )


def load_lambda_next_synthetic_experiment_readiness(
    path: str | Path,
) -> LambdaNextSyntheticExperimentReadiness:
    return LambdaNextSyntheticExperimentReadiness.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_next_synthetic_experiment_readiness(
    path: str | Path,
    report: LambdaNextSyntheticExperimentReadiness,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
