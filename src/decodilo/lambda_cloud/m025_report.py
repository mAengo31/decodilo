"""Combined M025 final Lambda pre-launch report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.final_prelaunch_evidence_package import (
    LambdaFinalPrelaunchEvidencePackage,
)
from decodilo.lambda_cloud.final_prelaunch_review import LambdaFinalPrelaunchReviewReport
from decodilo.lambda_cloud.go_no_go_record import LambdaGoNoGoRecord


class LambdaM025FinalPrelaunchReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_id: str = "lambda-m025-final-prelaunch-report"
    evidence_package: LambdaFinalPrelaunchEvidencePackage
    final_prelaunch_review: LambdaFinalPrelaunchReviewReport
    go_no_go_record: LambdaGoNoGoRecord
    future_first_launch_candidate: bool
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m025_report(
    *,
    evidence_package: LambdaFinalPrelaunchEvidencePackage,
    final_prelaunch_review: LambdaFinalPrelaunchReviewReport,
    go_no_go_record: LambdaGoNoGoRecord,
) -> LambdaM025FinalPrelaunchReport:
    return LambdaM025FinalPrelaunchReport(
        evidence_package=evidence_package,
        final_prelaunch_review=final_prelaunch_review,
        go_no_go_record=go_no_go_record,
        future_first_launch_candidate=(
            go_no_go_record.status == "go_for_future_m026_real_launch_review"
        ),
        warnings=[
            "M025 is final pre-launch review only; launch remains disabled.",
            *go_no_go_record.warnings,
        ],
        blockers=[*evidence_package.blockers, *final_prelaunch_review.blockers],
    )


def write_lambda_m025_report(path: str | Path, report: LambdaM025FinalPrelaunchReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
