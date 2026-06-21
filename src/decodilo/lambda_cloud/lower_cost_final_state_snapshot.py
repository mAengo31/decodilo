"""Fresh lower-cost state snapshot for future M039 review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.lower_cost_canonical_readiness import (
    LambdaLowerCostCanonicalReadinessReport,
    load_lambda_lower_cost_canonical_readiness,
)


class LambdaLowerCostFinalStateSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    snapshot_passed: bool
    required_endpoint_success: bool
    unmanaged_count: int
    unmanaged_billable_count: int
    selected_shape: str
    selected_region: str
    selected_ssh_key_hash: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostFinalStateSnapshot:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost state snapshot cannot enable launch")
        if self.snapshot_passed and self.blockers:
            raise ValueError("lower-cost state snapshot cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_final_state_snapshot(
    *,
    discovery: LambdaLiveDiscoveryReport,
    canonical_readiness: LambdaLowerCostCanonicalReadinessReport,
) -> LambdaLowerCostFinalStateSnapshot:
    blockers: list[str] = []
    unmanaged_count = len(discovery.unmanaged_instances)
    if not discovery.required_endpoint_success:
        blockers.append("required_endpoint_success_false")
    if unmanaged_count > 0:
        blockers.append("unmanaged_billable_resources_present")
    if not canonical_readiness.readiness_passed:
        blockers.extend(canonical_readiness.blockers or ["canonical_readiness_failed"])
    return LambdaLowerCostFinalStateSnapshot(
        snapshot_passed=not blockers,
        required_endpoint_success=discovery.required_endpoint_success,
        unmanaged_count=unmanaged_count,
        unmanaged_billable_count=unmanaged_count,
        selected_shape=canonical_readiness.shape,
        selected_region=canonical_readiness.region,
        selected_ssh_key_hash=canonical_readiness.selected_ssh_key_hash,
        blockers=sorted(set(blockers)),
        warnings=[
            "lower-cost state snapshot is read-only",
            *discovery.optional_endpoint_warnings,
        ],
    )


def build_lambda_lower_cost_final_state_snapshot_from_paths(
    *,
    discovery_report: str | Path,
    canonical_readiness: str | Path,
) -> LambdaLowerCostFinalStateSnapshot:
    return build_lambda_lower_cost_final_state_snapshot(
        discovery=load_lambda_live_discovery_report(discovery_report),
        canonical_readiness=load_lambda_lower_cost_canonical_readiness(
            canonical_readiness
        ),
    )


def load_lambda_lower_cost_final_state_snapshot(
    path: str | Path,
) -> LambdaLowerCostFinalStateSnapshot:
    return LambdaLowerCostFinalStateSnapshot.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_final_state_snapshot(
    path: str | Path,
    report: LambdaLowerCostFinalStateSnapshot,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
