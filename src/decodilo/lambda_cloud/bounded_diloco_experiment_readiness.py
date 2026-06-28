"""Readiness for the first complete bounded synthetic DiLoCo experiment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.scaffold_complete_decision import (
    load_lambda_scaffold_complete_decision,
)

LambdaBoundedDilocoExperimentReadinessStatus = Literal[
    "ready_for_first_bounded_synthetic_diloco_experiment_planning",
    "not_ready",
]


class LambdaBoundedDilocoExperimentReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M088"
    readiness_status: LambdaBoundedDilocoExperimentReadinessStatus
    cloud_lifecycle_ready: bool
    remote_source_dependency_path_ready: bool
    learner_syncer_protocol_ready: bool
    adamw_nesterov_optimizer_semantics_ready: bool
    integrated_protocol_optimizer_ready: bool
    synthetic_parameter_fragment_semantics_ready: bool
    next_step: str = "one_complete_bounded_synthetic_diloco_experiment"
    learners: int = 1
    sync_rounds: int = 1
    fragments: int = 2
    inner_optimizer: str = "adamw"
    outer_optimizer: str = "nesterov"
    max_steps: int = 1
    no_real_training: bool = True
    no_downloads: bool = True
    no_internet_install: bool = True
    no_background_process: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_readiness(self) -> LambdaBoundedDilocoExperimentReadiness:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("bounded experiment readiness must remain offline")
        if (
            self.readiness_status
            == "ready_for_first_bounded_synthetic_diloco_experiment_planning"
            and self.blockers
        ):
            raise ValueError("ready bounded experiment readiness cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_bounded_diloco_experiment_readiness_from_path(
    *,
    scaffold_decision: str | Path,
) -> LambdaBoundedDilocoExperimentReadiness:
    decision = load_lambda_scaffold_complete_decision(scaffold_decision)
    ready = decision.scaffold_status == "scaffold_validation_complete"
    blockers = [] if ready else ["scaffold_validation_not_complete"]
    return LambdaBoundedDilocoExperimentReadiness(
        readiness_status=(
            "ready_for_first_bounded_synthetic_diloco_experiment_planning"
            if ready
            else "not_ready"
        ),
        cloud_lifecycle_ready=ready,
        remote_source_dependency_path_ready=ready,
        learner_syncer_protocol_ready=ready,
        adamw_nesterov_optimizer_semantics_ready=ready,
        integrated_protocol_optimizer_ready=ready,
        synthetic_parameter_fragment_semantics_ready=ready,
        blockers=blockers,
        warnings=[
            "readiness is planning-only and does not authorize launch",
            "next live milestone should be a complete bounded experiment, not another "
            "standalone scaffold category",
        ],
    )


def load_lambda_bounded_diloco_experiment_readiness(
    path: str | Path,
) -> LambdaBoundedDilocoExperimentReadiness:
    return LambdaBoundedDilocoExperimentReadiness.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_bounded_diloco_experiment_readiness(
    path: str | Path,
    report: LambdaBoundedDilocoExperimentReadiness,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
