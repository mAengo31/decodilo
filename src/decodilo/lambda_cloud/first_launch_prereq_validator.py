"""Prerequisite validator for M025 final pre-launch evidence."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.final_prelaunch_evidence_package import (
    LambdaFinalPrelaunchEvidencePackage,
    load_lambda_final_prelaunch_evidence_package,
)


class LambdaFirstLaunchPrereqValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    prereq_passed_for_review: bool
    missing_items: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def validate_lambda_first_launch_prereqs(
    evidence_package: str | Path | LambdaFinalPrelaunchEvidencePackage,
) -> LambdaFirstLaunchPrereqValidationReport:
    package = (
        evidence_package
        if isinstance(evidence_package, LambdaFinalPrelaunchEvidencePackage)
        else load_lambda_final_prelaunch_evidence_package(evidence_package)
    )
    return LambdaFirstLaunchPrereqValidationReport(
        prereq_passed_for_review=package.evidence_complete,
        missing_items=package.missing_items,
        blockers=package.blockers,
        warnings=["Prerequisite validation is review-only and cannot enable launch."],
    )


def write_lambda_first_launch_prereq_validation_report(
    path: str | Path,
    report: LambdaFirstLaunchPrereqValidationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
