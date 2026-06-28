"""Future first bounded synthetic runtime experiment readiness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.runtime_smoke_closeout import (
    load_lambda_runtime_smoke_closeout,
)

LambdaFirstSyntheticExperimentReadinessStatus = Literal[
    "ready_for_future_first_synthetic_experiment_planning",
    "not_ready",
]


class LambdaFirstSyntheticExperimentReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M076"
    readiness_status: LambdaFirstSyntheticExperimentReadinessStatus
    cloud_lifecycle_ready: bool
    ssh_ready: bool
    source_bundle_ready: bool
    dependency_bundle_ready: bool
    local_only_dependency_install_ready: bool
    decodilo_cli_ready: bool
    runtime_protocol_smoke_ready: bool
    next_experiment_must_remain_bounded_and_synthetic: bool = True
    one_instance_default: bool = True
    no_model_or_data_download: bool = True
    no_internet_package_install: bool = True
    no_long_training: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_readiness(self) -> LambdaFirstSyntheticExperimentReadiness:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("first synthetic experiment readiness must remain offline")
        if (
            self.readiness_status
            == "ready_for_future_first_synthetic_experiment_planning"
            and self.blockers
        ):
            raise ValueError("ready first synthetic readiness cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_first_synthetic_experiment_readiness_from_path(
    *,
    runtime_smoke_closeout: str | Path,
) -> LambdaFirstSyntheticExperimentReadiness:
    closeout = load_lambda_runtime_smoke_closeout(runtime_smoke_closeout)
    ready = closeout.closeout_succeeded and closeout.runtime_smoke_success
    blockers = [] if ready else ["runtime_smoke_closeout_not_succeeded"]
    return LambdaFirstSyntheticExperimentReadiness(
        readiness_status=(
            "ready_for_future_first_synthetic_experiment_planning"
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
        blockers=blockers,
        warnings=[
            "readiness is planning-only and does not authorize launch",
            "first synthetic experiment must remain bounded, synthetic, and no-download",
        ],
    )


def load_lambda_first_synthetic_experiment_readiness(
    path: str | Path,
) -> LambdaFirstSyntheticExperimentReadiness:
    return LambdaFirstSyntheticExperimentReadiness.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_first_synthetic_experiment_readiness(
    path: str | Path,
    report: LambdaFirstSyntheticExperimentReadiness,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
