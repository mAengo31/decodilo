"""Future bounded DiLoCo optimizer-fidelity readiness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_synthetic_closeout import (
    load_lambda_diloco_synthetic_closeout,
)

LambdaDilocoOptimizerReadinessStatus = Literal[
    "ready_for_future_diloco_optimizer_planning",
    "not_ready",
]


class LambdaDilocoOptimizerReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M082"
    readiness_status: LambdaDilocoOptimizerReadinessStatus
    cloud_lifecycle_ready: bool
    remote_source_dependency_path_ready: bool
    remote_diloco_shaped_protocol_smoke_ready: bool
    next_step_should_focus_on_optimizer_fidelity: bool = True
    desired_inner_adamw_semantics: bool = True
    desired_outer_nesterov_semantics: bool = True
    desired_pseudo_gradient_semantics: bool = True
    desired_persistent_optimizer_state: bool = True
    deterministic_tiny_synthetic_test_required: bool = True
    no_real_model_training: bool = True
    no_model_or_data_download: bool = True
    no_internet_package_install: bool = True
    one_instance_default: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_readiness(self) -> LambdaDilocoOptimizerReadiness:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("DiLoCo optimizer readiness must remain offline")
        if (
            self.readiness_status == "ready_for_future_diloco_optimizer_planning"
            and self.blockers
        ):
            raise ValueError("ready DiLoCo optimizer readiness cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_diloco_optimizer_readiness_from_path(
    *,
    diloco_synthetic_closeout: str | Path,
) -> LambdaDilocoOptimizerReadiness:
    closeout = load_lambda_diloco_synthetic_closeout(diloco_synthetic_closeout)
    ready = (
        closeout.closeout_succeeded
        and closeout.diloco_synthetic_success
        and closeout.optimizer_claim_honesty_confirmed
        and closeout.optimization_fidelity == "diloco_shaped_protocol_only"
    )
    blockers = [] if ready else ["diloco_synthetic_closeout_not_ready"]
    return LambdaDilocoOptimizerReadiness(
        readiness_status=(
            "ready_for_future_diloco_optimizer_planning" if ready else "not_ready"
        ),
        cloud_lifecycle_ready=ready,
        remote_source_dependency_path_ready=ready,
        remote_diloco_shaped_protocol_smoke_ready=ready,
        blockers=blockers,
        warnings=[
            "readiness is planning-only and does not authorize launch",
            "future optimizer smoke must remain bounded, synthetic, and no-training",
        ],
    )


def load_lambda_diloco_optimizer_readiness(
    path: str | Path,
) -> LambdaDilocoOptimizerReadiness:
    return LambdaDilocoOptimizerReadiness.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_diloco_optimizer_readiness(
    path: str | Path,
    report: LambdaDilocoOptimizerReadiness,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
