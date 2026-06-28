"""First remote Decodilo experiment readiness after M069R."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_decodilo_vslice_closeout import (
    load_lambda_remote_decodilo_vslice_closeout,
)

LambdaFirstExperimentReadinessStatus = Literal[
    "ready_for_future_first_experiment_planning",
    "not_ready",
]


class LambdaFirstExperimentReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M070"
    readiness_status: LambdaFirstExperimentReadinessStatus
    cloud_lifecycle_ready: bool
    ssh_ready: bool
    source_upload_ready: bool
    dependency_bundle_ready: bool
    decodilo_cli_ready: bool
    first_experiment_must_be_tiny_and_bounded: bool = True
    no_package_internet_install: bool = True
    no_data_or_model_download_without_separate_approval: bool = True
    no_long_training: bool = True
    one_instance_default: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_readiness(self) -> LambdaFirstExperimentReadiness:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M070 readiness must be future-only")
        if self.readiness_status == "ready_for_future_first_experiment_planning" and self.blockers:
            raise ValueError("ready first-experiment readiness cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_first_experiment_readiness_from_path(
    *,
    closeout: str | Path,
) -> LambdaFirstExperimentReadiness:
    close = load_lambda_remote_decodilo_vslice_closeout(closeout)
    ready = close.closeout_succeeded
    blockers = [] if ready else ["remote_decodilo_vslice_closeout_not_succeeded"]
    return LambdaFirstExperimentReadiness(
        readiness_status=(
            "ready_for_future_first_experiment_planning" if ready else "not_ready"
        ),
        cloud_lifecycle_ready=ready,
        ssh_ready=ready,
        source_upload_ready=ready,
        dependency_bundle_ready=ready,
        decodilo_cli_ready=ready,
        blockers=blockers,
        warnings=[
            "readiness does not authorize launch; M071R still needs explicit operator approval",
            (
                "first experiment must remain tiny, bounded, and no-download "
                "unless separately approved"
            ),
        ],
    )


def load_lambda_first_experiment_readiness(path: str | Path) -> LambdaFirstExperimentReadiness:
    return LambdaFirstExperimentReadiness.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_first_experiment_readiness(
    path: str | Path,
    report: LambdaFirstExperimentReadiness,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
