"""Future bounded DiLoCo-shaped synthetic experiment readiness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.learner_syncer_smoke_closeout import (
    load_lambda_learner_syncer_smoke_closeout,
)

LambdaDilocoSyntheticReadinessStatus = Literal[
    "ready_for_future_diloco_synthetic_planning",
    "not_ready",
]


class LambdaDilocoSyntheticReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M080"
    readiness_status: LambdaDilocoSyntheticReadinessStatus
    cloud_lifecycle_ready: bool
    ssh_ready: bool
    source_bundle_ready: bool
    dependency_bundle_ready: bool
    local_only_dependency_install_ready: bool
    decodilo_cli_ready: bool
    runtime_protocol_smoke_ready: bool
    learner_syncer_smoke_ready: bool
    next_experiment_must_remain_bounded_and_synthetic: bool = True
    next_experiment_may_be_diloco_shaped_no_real_training: bool = True
    one_instance_default: bool = True
    one_sync_update_round_default: bool = True
    no_model_or_data_download: bool = True
    no_internet_package_install: bool = True
    no_real_training: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_readiness(self) -> LambdaDilocoSyntheticReadiness:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("DiLoCo synthetic readiness must remain offline")
        if self.readiness_status == "ready_for_future_diloco_synthetic_planning" and self.blockers:
            raise ValueError("ready DiLoCo synthetic readiness cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_diloco_synthetic_readiness_from_path(
    *,
    learner_syncer_closeout: str | Path,
) -> LambdaDilocoSyntheticReadiness:
    closeout = load_lambda_learner_syncer_smoke_closeout(learner_syncer_closeout)
    ready = closeout.closeout_succeeded and closeout.learner_syncer_smoke_success
    blockers = [] if ready else ["learner_syncer_smoke_closeout_not_succeeded"]
    return LambdaDilocoSyntheticReadiness(
        readiness_status=(
            "ready_for_future_diloco_synthetic_planning" if ready else "not_ready"
        ),
        cloud_lifecycle_ready=ready,
        ssh_ready=ready,
        source_bundle_ready=ready,
        dependency_bundle_ready=ready,
        local_only_dependency_install_ready=ready,
        decodilo_cli_ready=ready,
        runtime_protocol_smoke_ready=ready,
        learner_syncer_smoke_ready=ready,
        blockers=blockers,
        warnings=[
            "readiness is planning-only and does not authorize launch",
            "future DiLoCo-shaped step must remain bounded, synthetic, and no-training",
        ],
    )


def load_lambda_diloco_synthetic_readiness(
    path: str | Path,
) -> LambdaDilocoSyntheticReadiness:
    return LambdaDilocoSyntheticReadiness.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_diloco_synthetic_readiness(
    path: str | Path,
    report: LambdaDilocoSyntheticReadiness,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
