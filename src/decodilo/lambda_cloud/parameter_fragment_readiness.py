"""Future bounded parameter-fragment synthetic readiness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.integrated_diloco_closeout import (
    load_lambda_integrated_diloco_closeout,
)

LambdaParameterFragmentReadinessStatus = Literal[
    "ready_for_future_parameter_fragment_planning",
    "not_ready",
]


class LambdaParameterFragmentReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M086"
    readiness_status: LambdaParameterFragmentReadinessStatus
    cloud_lifecycle_ready: bool
    remote_source_dependency_path_ready: bool
    remote_integrated_diloco_synthetic_smoke_ready: bool
    next_scientific_gap: str = "parameter_fragment_semantics"
    deterministic_fragment_definition_required: bool = True
    fragment_update_required: bool = True
    fragment_schedule_required: bool = True
    per_fragment_version_state_required: bool = True
    merge_replay_validation_required: bool = True
    no_overlap_claim_unless_implemented: bool = True
    no_quantization_claim_unless_implemented: bool = True
    one_instance_default: bool = True
    no_real_training: bool = True
    no_model_or_data_download: bool = True
    no_internet_package_install: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_readiness(self) -> LambdaParameterFragmentReadiness:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("parameter-fragment readiness must remain offline")
        if (
            self.readiness_status == "ready_for_future_parameter_fragment_planning"
            and self.blockers
        ):
            raise ValueError("ready parameter-fragment readiness cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_parameter_fragment_readiness_from_path(
    *,
    integrated_diloco_closeout: str | Path,
) -> LambdaParameterFragmentReadiness:
    closeout = load_lambda_integrated_diloco_closeout(integrated_diloco_closeout)
    ready = bool(
        closeout.closeout_succeeded
        and closeout.integrated_diloco_success
        and closeout.integrated_semantics_confirmed
        and closeout.optimization_fidelity == "integrated_optimizer_protocol_smoke"
        and closeout.parameter_fragment_semantics == "not_exercised"
    )
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("integrated_diloco_closeout_not_succeeded")
    if not closeout.integrated_diloco_success:
        blockers.append("integrated_diloco_success_not_confirmed")
    if not closeout.integrated_semantics_confirmed:
        blockers.append("integrated_semantics_not_confirmed")
    if closeout.parameter_fragment_semantics != "not_exercised":
        blockers.append("parameter_fragment_gap_not_clearly_open")
    return LambdaParameterFragmentReadiness(
        readiness_status=(
            "ready_for_future_parameter_fragment_planning" if ready else "not_ready"
        ),
        cloud_lifecycle_ready=ready,
        remote_source_dependency_path_ready=ready,
        remote_integrated_diloco_synthetic_smoke_ready=ready,
        blockers=blockers,
        warnings=[
            "readiness is planning-only and does not authorize launch",
            "future parameter-fragment smoke must remain bounded, synthetic, "
            "and no-training",
        ],
    )


def load_lambda_parameter_fragment_readiness(
    path: str | Path,
) -> LambdaParameterFragmentReadiness:
    return LambdaParameterFragmentReadiness.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_parameter_fragment_readiness(
    path: str | Path,
    report: LambdaParameterFragmentReadiness,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
