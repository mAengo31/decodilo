"""Validator for M026 Lambda human review manifests."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.human_review_manifest import (
    LambdaHumanReviewManifest,
    load_lambda_human_review_manifest,
)


class LambdaHumanReviewValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    human_review_valid_for_m027_authorization: bool
    requested_decision: str
    missing_acknowledgements: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaHumanReviewValidator:
    def validate(
        self,
        manifest: str | Path | LambdaHumanReviewManifest,
    ) -> LambdaHumanReviewValidationReport:
        effective = (
            manifest
            if isinstance(manifest, LambdaHumanReviewManifest)
            else load_lambda_human_review_manifest(manifest)
        )
        missing = effective.acknowledgements.missing()
        blockers = [f"missing acknowledgement: {item}" for item in missing]
        if not effective.human_review_complete:
            blockers.append("human_review_complete=false")
        if effective.max_budget > 50:
            blockers.append("max budget exceeds 50")
        if effective.max_runtime_minutes > 30:
            blockers.append("max runtime exceeds 30 minutes")
        if effective.max_instances > 1:
            blockers.append("max instances exceeds one")
        if effective.requested_decision != "approve_m027_minimal_real_mutation_implementation":
            blockers.append("review did not request M027 implementation authorization")
        return LambdaHumanReviewValidationReport(
            human_review_valid_for_m027_authorization=not blockers,
            requested_decision=effective.requested_decision,
            missing_acknowledgements=missing,
            blockers=blockers,
            warnings=["Human review can authorize M027 implementation planning only."],
        )


def validate_lambda_human_review(
    manifest: str | Path | LambdaHumanReviewManifest,
) -> LambdaHumanReviewValidationReport:
    return LambdaHumanReviewValidator().validate(manifest)


def load_lambda_human_review_validation_report(
    path: str | Path,
) -> LambdaHumanReviewValidationReport:
    return LambdaHumanReviewValidationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_human_review_validation_report(
    path: str | Path,
    report: LambdaHumanReviewValidationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
