"""Preflight checks for M029B Lambda shape evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.availability_evidence import LambdaAvailabilityEvidence
from decodilo.lambda_cloud.launch_shape_resolution import LambdaLaunchShapeResolutionReport
from decodilo.lambda_cloud.non_sample_price_snapshot import LambdaNonSamplePriceSnapshotReport
from decodilo.lambda_cloud.shape_evidence import LambdaShapeEvidenceReport


class LambdaShapeEvidencePreflightReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preflight_passed: bool
    shape_gate_passed: bool
    price_gate_passed: bool
    live_availability_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_shape_evidence_preflight(
    *,
    shape_evidence: LambdaShapeEvidenceReport,
    price_snapshot: LambdaNonSamplePriceSnapshotReport,
    availability: LambdaAvailabilityEvidence,
    resolution: LambdaLaunchShapeResolutionReport,
) -> LambdaShapeEvidencePreflightReport:
    blockers: list[str] = []
    if not shape_evidence.first_launch_evidence_usable:
        blockers.extend(shape_evidence.blockers)
    if not price_snapshot.non_sample_price_snapshot_passed:
        blockers.extend(price_snapshot.blockers)
    if not resolution.first_launch_allowed_by_shape_evidence:
        blockers.extend(resolution.errors)
    return LambdaShapeEvidencePreflightReport(
        preflight_passed=not blockers,
        shape_gate_passed=resolution.first_launch_allowed_by_shape_evidence,
        price_gate_passed=price_snapshot.non_sample_price_snapshot_passed,
        live_availability_status=availability.status,
        blockers=blockers,
        warnings=[
            *shape_evidence.warnings,
            *price_snapshot.warnings,
            *availability.warnings,
            *resolution.warnings,
        ],
    )


def write_lambda_shape_evidence_preflight_report(
    path: str | Path,
    report: LambdaShapeEvidencePreflightReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
