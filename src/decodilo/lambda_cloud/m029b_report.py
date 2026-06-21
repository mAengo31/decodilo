"""Combined M029B shape and price evidence report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.availability_evidence import (
    LambdaAvailabilityEvidence,
    load_lambda_availability_evidence,
)
from decodilo.lambda_cloud.launch_shape_resolution import (
    LambdaLaunchShapeResolutionReport,
    load_lambda_launch_shape_resolution_report,
)
from decodilo.lambda_cloud.m028_report import LambdaM028Report, load_lambda_m028_report
from decodilo.lambda_cloud.m029_launch_authorization import (
    LambdaM029AuthorizationPackage,
    load_lambda_m029_authorization_package,
)
from decodilo.lambda_cloud.non_sample_price_snapshot import (
    LambdaNonSamplePriceSnapshotReport,
    validate_non_sample_price_snapshot_from_path,
)


class LambdaM029BReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    product_catalog_evidence_present: bool
    non_sample_price_snapshot: LambdaNonSamplePriceSnapshotReport
    availability_evidence: LambdaAvailabilityEvidence | None = None
    launch_shape_resolution: LambdaLaunchShapeResolutionReport
    m028_regeneration_status: str
    m029_authorization_status: str
    shape_gate_passed: bool
    price_gate_passed: bool
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommended_next_step: str

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m029b_report(
    *,
    shape_resolution: str | Path | LambdaLaunchShapeResolutionReport,
    price_snapshot: str | Path,
    m028_report: str | Path | LambdaM028Report | None = None,
    m029_authorization: str | Path | LambdaM029AuthorizationPackage | None = None,
    availability_evidence: str | Path | LambdaAvailabilityEvidence | None = None,
) -> LambdaM029BReport:
    resolution = (
        shape_resolution
        if isinstance(shape_resolution, LambdaLaunchShapeResolutionReport)
        else load_lambda_launch_shape_resolution_report(shape_resolution)
    )
    price = validate_non_sample_price_snapshot_from_path(price_snapshot)
    availability = _load_availability(availability_evidence)
    m028 = _load_m028(m028_report)
    auth = _load_auth(m029_authorization)
    blockers = [*price.blockers, *resolution.errors]
    if auth is not None and not auth.package_passed:
        blockers.extend(auth.blockers)
    m028_status = "not_regenerated"
    if m028 is not None:
        m028_status = "passed" if m028.report_passed else "blocked"
    auth_status = "not_available"
    if auth is not None:
        auth_status = "passed" if auth.package_passed else "blocked"
    shape_gate = resolution.first_launch_allowed_by_shape_evidence
    price_gate = price.non_sample_price_snapshot_passed
    return LambdaM029BReport(
        product_catalog_evidence_present=resolution.matched_product_catalog_record is not None,
        non_sample_price_snapshot=price,
        availability_evidence=availability,
        launch_shape_resolution=resolution,
        m028_regeneration_status=m028_status,
        m029_authorization_status=auth_status,
        shape_gate_passed=shape_gate,
        price_gate_passed=price_gate,
        blockers=blockers,
        warnings=[
            *price.warnings,
            *resolution.warnings,
            *(availability.warnings if availability else []),
        ],
        recommended_next_step=(
            "Regenerate M020/M028/M029 gates with resolved shape evidence; do not launch in M029B."
            if shape_gate and price_gate
            else "Fix shape or non-sample price evidence before another M029 attempt."
        ),
    )


def _load_m028(value: str | Path | LambdaM028Report | None) -> LambdaM028Report | None:
    if value is None or isinstance(value, LambdaM028Report):
        return value
    return load_lambda_m028_report(value)


def _load_auth(
    value: str | Path | LambdaM029AuthorizationPackage | None,
) -> LambdaM029AuthorizationPackage | None:
    if value is None or isinstance(value, LambdaM029AuthorizationPackage):
        return value
    return load_lambda_m029_authorization_package(value)


def _load_availability(
    value: str | Path | LambdaAvailabilityEvidence | None,
) -> LambdaAvailabilityEvidence | None:
    if value is None or isinstance(value, LambdaAvailabilityEvidence):
        return value
    return load_lambda_availability_evidence(value)


def load_lambda_m029b_report(path: str | Path) -> LambdaM029BReport:
    return LambdaM029BReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m029b_report(path: str | Path, report: LambdaM029BReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
