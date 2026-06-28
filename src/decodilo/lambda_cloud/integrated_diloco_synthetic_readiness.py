"""Future bounded integrated synthetic DiLoCo readiness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_optimizer_closeout import (
    load_lambda_diloco_optimizer_closeout,
)
from decodilo.lambda_cloud.diloco_synthetic_closeout import (
    load_lambda_diloco_synthetic_closeout,
)
from decodilo.lambda_cloud.learner_syncer_smoke_closeout import (
    load_lambda_learner_syncer_smoke_closeout,
)

LambdaIntegratedDilocoReadinessStatus = Literal[
    "ready_for_future_integrated_diloco_planning",
    "not_ready",
]


class LambdaIntegratedDilocoSyntheticReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M084"
    readiness_status: LambdaIntegratedDilocoReadinessStatus
    cloud_lifecycle_ready: bool
    ssh_ready_for_proven_candidates: bool
    remote_source_dependency_path_ready: bool
    remote_learner_syncer_smoke_ready: bool
    remote_diloco_shaped_protocol_smoke_ready: bool
    remote_optimizer_fidelity_smoke_ready: bool
    next_step_should_integrate_protocol_and_optimizer_semantics: bool = True
    one_instance_default: bool = True
    learners_default: int = 1
    sync_rounds_default: int = 1
    inner_optimizer_required: str = "adamw"
    outer_optimizer_required: str = "nesterov"
    no_real_training: bool = True
    no_model_or_data_download: bool = True
    no_internet_package_install: bool = True
    no_parameter_fragment_claim_unless_active: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_readiness(self) -> LambdaIntegratedDilocoSyntheticReadiness:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("integrated DiLoCo readiness must remain offline")
        if (
            self.readiness_status == "ready_for_future_integrated_diloco_planning"
            and self.blockers
        ):
            raise ValueError("ready integrated DiLoCo readiness cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_integrated_diloco_synthetic_readiness_from_paths(
    *,
    diloco_synthetic_closeout: str | Path,
    optimizer_closeout: str | Path,
    learner_syncer_closeout: str | Path,
) -> LambdaIntegratedDilocoSyntheticReadiness:
    diloco_closeout = load_lambda_diloco_synthetic_closeout(diloco_synthetic_closeout)
    optimizer = load_lambda_diloco_optimizer_closeout(optimizer_closeout)
    learner_syncer = load_lambda_learner_syncer_smoke_closeout(learner_syncer_closeout)
    learner_ready = bool(
        learner_syncer.closeout_succeeded
        and learner_syncer.learner_syncer_smoke_success
    )
    diloco_ready = bool(
        diloco_closeout.closeout_succeeded and diloco_closeout.diloco_synthetic_success
    )
    optimizer_ready = bool(
        optimizer.closeout_succeeded
        and optimizer.diloco_optimizer_success
        and optimizer.optimizer_semantics_confirmed
        and optimizer.optimization_fidelity == "optimizer_semantics_smoke"
    )
    ready = learner_ready and diloco_ready and optimizer_ready
    blockers: list[str] = []
    if not learner_ready:
        blockers.append("learner_syncer_closeout_not_ready")
    if not diloco_ready:
        blockers.append("diloco_synthetic_closeout_not_ready")
    if not optimizer_ready:
        blockers.append("diloco_optimizer_closeout_not_ready")
    return LambdaIntegratedDilocoSyntheticReadiness(
        readiness_status=(
            "ready_for_future_integrated_diloco_planning" if ready else "not_ready"
        ),
        cloud_lifecycle_ready=ready,
        ssh_ready_for_proven_candidates=ready,
        remote_source_dependency_path_ready=ready,
        remote_learner_syncer_smoke_ready=learner_ready,
        remote_diloco_shaped_protocol_smoke_ready=diloco_ready,
        remote_optimizer_fidelity_smoke_ready=optimizer_ready,
        blockers=blockers,
        warnings=[
            "readiness is planning-only and does not authorize launch",
            "future integrated smoke must remain bounded, synthetic, and no-training",
        ],
    )


def load_lambda_integrated_diloco_synthetic_readiness(
    path: str | Path,
) -> LambdaIntegratedDilocoSyntheticReadiness:
    return LambdaIntegratedDilocoSyntheticReadiness.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_integrated_diloco_synthetic_readiness(
    path: str | Path,
    report: LambdaIntegratedDilocoSyntheticReadiness,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
