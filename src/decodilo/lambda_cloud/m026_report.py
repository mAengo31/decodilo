"""Combined M026 Lambda implementation authorization decision report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.evidence_freshness import LambdaEvidenceFreshnessReport
from decodilo.lambda_cloud.human_review_validator import LambdaHumanReviewValidationReport
from decodilo.lambda_cloud.m027_authorization_record import LambdaM027AuthorizationRecord
from decodilo.lambda_cloud.prelaunch_fresh_readonly_check import (
    LambdaPrelaunchFreshReadOnlyCheck,
)
from decodilo.lambda_cloud.real_launch_blocker_matrix import LambdaRealLaunchBlockerMatrix
from decodilo.lambda_cloud.real_launch_decision_record import LambdaRealLaunchDecisionRecord


class LambdaM026DecisionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_id: str = "lambda-m026-decision-report"
    human_review_validation: LambdaHumanReviewValidationReport | None = None
    evidence_freshness: LambdaEvidenceFreshnessReport | None = None
    blocker_matrix: LambdaRealLaunchBlockerMatrix | None = None
    decision_record: LambdaRealLaunchDecisionRecord
    m027_authorization_record: LambdaM027AuthorizationRecord
    fresh_readonly_check: LambdaPrelaunchFreshReadOnlyCheck | None = None
    secret_scan_status: str = "not_checked"
    semantic_audit_status: str = "not_included"
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m026_report(
    *,
    decision_record: LambdaRealLaunchDecisionRecord,
    authorization_record: LambdaM027AuthorizationRecord,
    human_review_validation: LambdaHumanReviewValidationReport | None = None,
    evidence_freshness: LambdaEvidenceFreshnessReport | None = None,
    blocker_matrix: LambdaRealLaunchBlockerMatrix | None = None,
) -> LambdaM026DecisionReport:
    blockers = [*decision_record.blockers]
    if blocker_matrix is not None:
        blockers.extend(
            blocker.message
            for blocker in blocker_matrix.blockers
            if blocker.blocks_m027_implementation_authorization
        )
    return LambdaM026DecisionReport(
        human_review_validation=human_review_validation,
        evidence_freshness=evidence_freshness,
        blocker_matrix=blocker_matrix,
        decision_record=decision_record,
        m027_authorization_record=authorization_record,
        warnings=[
            "M026 report can authorize implementation work only; launch remains disabled.",
            *decision_record.warnings,
        ],
        blockers=blockers,
    )


def write_lambda_m026_report(path: str | Path, report: LambdaM026DecisionReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
