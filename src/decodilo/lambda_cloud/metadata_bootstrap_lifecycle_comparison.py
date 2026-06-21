"""Compare M051B metadata bootstrap against the prior lifecycle smoke closeout."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lifecycle_smoke_closeout import (
    load_lambda_lifecycle_smoke_closeout,
)
from decodilo.lambda_cloud.lifecycle_smoke_success_record import (
    load_lambda_lifecycle_smoke_success_record,
)
from decodilo.lambda_cloud.metadata_bootstrap_closeout import (
    load_lambda_metadata_bootstrap_closeout,
)
from decodilo.lambda_cloud.metadata_bootstrap_success_record import (
    load_lambda_metadata_bootstrap_success_record,
)


class LambdaMetadataBootstrapLifecycleComparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    lifecycle_smoke_success: bool
    metadata_bootstrap_success: bool
    selected_candidate_lifecycle: str | None = None
    selected_candidate_metadata: str | None = None
    selected_region_lifecycle: str | None = None
    selected_region_metadata: str | None = None
    launch_latency_comparison: dict[str, float | None] = Field(default_factory=dict)
    termination_latency_comparison: dict[str, float | None] = Field(default_factory=dict)
    spend_comparison: dict[str, float | None] = Field(default_factory=dict)
    added_capability: list[str] = Field(default_factory=list)
    still_not_done: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaMetadataBootstrapLifecycleComparison:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("metadata lifecycle comparison cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_metadata_bootstrap_lifecycle_comparison_from_paths(
    *,
    lifecycle_closeout: str | Path,
    metadata_closeout: str | Path,
    lifecycle_success_record: str | Path | None = None,
    metadata_success_record: str | Path | None = None,
) -> LambdaMetadataBootstrapLifecycleComparison:
    lifecycle = load_lambda_lifecycle_smoke_closeout(lifecycle_closeout)
    metadata = load_lambda_metadata_bootstrap_closeout(metadata_closeout)
    lifecycle_success = (
        None
        if lifecycle_success_record is None or not Path(lifecycle_success_record).exists()
        else load_lambda_lifecycle_smoke_success_record(lifecycle_success_record)
    )
    metadata_success = (
        None
        if metadata_success_record is None or not Path(metadata_success_record).exists()
        else load_lambda_metadata_bootstrap_success_record(metadata_success_record)
    )
    blockers: list[str] = []
    if not lifecycle.closeout_succeeded:
        blockers.append("lifecycle_closeout_not_succeeded")
    if not metadata.closeout_succeeded:
        blockers.append("metadata_closeout_not_succeeded")
    return LambdaMetadataBootstrapLifecycleComparison(
        lifecycle_smoke_success=lifecycle.closeout_succeeded,
        metadata_bootstrap_success=metadata.closeout_succeeded,
        selected_candidate_lifecycle=(
            None if lifecycle_success is None else lifecycle_success.selected_candidate
        ),
        selected_candidate_metadata=metadata.selected_candidate,
        selected_region_lifecycle=(
            None if lifecycle_success is None else lifecycle_success.selected_region
        ),
        selected_region_metadata=metadata.selected_region,
        launch_latency_comparison={
            "lifecycle_elapsed_seconds": (
                None if lifecycle_success is None else lifecycle_success.elapsed_seconds
            ),
            "metadata_elapsed_seconds": (
                None if metadata_success is None else metadata_success.elapsed_seconds
            ),
        },
        termination_latency_comparison={
            "lifecycle_termination_verified": float(lifecycle.termination_verified),
            "metadata_termination_verified": float(metadata.termination_verified),
        },
        spend_comparison={
            "lifecycle_estimated_spend": (
                None if lifecycle_success is None else lifecycle_success.estimated_spend
            ),
            "metadata_estimated_spend": (
                None if metadata_success is None else metadata_success.estimated_spend
            ),
        },
        added_capability=["provider_metadata_collected"],
        still_not_done=[
            "SSH",
            "remote commands",
            "package install",
            "training",
            "distributed runtime",
        ],
        blockers=sorted(set(blockers)),
        warnings=["M052 comparison is informational and does not authorize execution"],
    )


def load_lambda_metadata_bootstrap_lifecycle_comparison(
    path: str | Path,
) -> LambdaMetadataBootstrapLifecycleComparison:
    return LambdaMetadataBootstrapLifecycleComparison.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_metadata_bootstrap_lifecycle_comparison(
    path: str | Path,
    report: LambdaMetadataBootstrapLifecycleComparison,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
