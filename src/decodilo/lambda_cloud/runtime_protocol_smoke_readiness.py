"""Future runtime/protocol smoke readiness after successful tiny-smoke."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.tiny_smoke_closeout import load_lambda_tiny_smoke_closeout

LambdaRuntimeProtocolSmokeReadinessStatus = Literal[
    "ready_for_future_runtime_protocol_smoke_planning",
    "not_ready",
]


class LambdaRuntimeProtocolSmokeReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M074"
    readiness_status: LambdaRuntimeProtocolSmokeReadinessStatus
    cloud_lifecycle_ready: bool
    ssh_ready: bool
    source_bundle_ready: bool
    dependency_bundle_ready: bool
    decodilo_cli_ready: bool
    tiny_smoke_ready: bool
    next_smoke_must_be_bounded_and_synthetic: bool = True
    no_model_or_data_download: bool = True
    no_internet_package_install: bool = True
    no_long_training: bool = True
    one_instance_default: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_readiness(self) -> LambdaRuntimeProtocolSmokeReadiness:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("runtime/protocol readiness must remain future-only")
        if (
            self.readiness_status == "ready_for_future_runtime_protocol_smoke_planning"
            and self.blockers
        ):
            raise ValueError("ready runtime/protocol readiness cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_runtime_protocol_smoke_readiness_from_path(
    *,
    tiny_smoke_closeout: str | Path,
) -> LambdaRuntimeProtocolSmokeReadiness:
    closeout = load_lambda_tiny_smoke_closeout(tiny_smoke_closeout)
    ready = closeout.closeout_succeeded and closeout.tiny_smoke_success
    blockers = [] if ready else ["tiny_smoke_closeout_not_succeeded"]
    return LambdaRuntimeProtocolSmokeReadiness(
        readiness_status=(
            "ready_for_future_runtime_protocol_smoke_planning" if ready else "not_ready"
        ),
        cloud_lifecycle_ready=ready,
        ssh_ready=ready,
        source_bundle_ready=ready,
        dependency_bundle_ready=ready,
        decodilo_cli_ready=ready,
        tiny_smoke_ready=ready,
        blockers=blockers,
        warnings=[
            "readiness does not authorize launch; M075R requires explicit future approval",
            "runtime/protocol smoke must remain synthetic, bounded, and no-download",
        ],
    )


def load_lambda_runtime_protocol_smoke_readiness(
    path: str | Path,
) -> LambdaRuntimeProtocolSmokeReadiness:
    return LambdaRuntimeProtocolSmokeReadiness.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_runtime_protocol_smoke_readiness(
    path: str | Path,
    report: LambdaRuntimeProtocolSmokeReadiness,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
