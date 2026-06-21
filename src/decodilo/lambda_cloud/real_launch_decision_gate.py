"""Decision gate for M026 Lambda M027 implementation authorization."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.evidence_freshness import (
    LambdaEvidenceFreshnessReport,
    load_lambda_evidence_freshness_report,
)
from decodilo.lambda_cloud.final_prelaunch_review import (
    LambdaFinalPrelaunchReviewReport,
    load_lambda_final_prelaunch_review,
)
from decodilo.lambda_cloud.human_review_validator import (
    LambdaHumanReviewValidationReport,
    load_lambda_human_review_validation_report,
)
from decodilo.lambda_cloud.real_launch_blocker_matrix import (
    LambdaRealLaunchBlockerMatrix,
    load_lambda_real_launch_blocker_matrix,
)
from decodilo.lambda_cloud.real_launch_decision_record import (
    LambdaRealLaunchDecisionRecord,
    LambdaRealLaunchDecisionStatus,
)


class LambdaRealLaunchDecisionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_record: LambdaRealLaunchDecisionRecord
    human_review_valid: bool
    freshness_passed: bool
    m027_authorization_blocked: bool
    m025_review_recommendation: str
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRealLaunchDecisionGate:
    def decide(
        self,
        *,
        human_review_validation: str | Path | LambdaHumanReviewValidationReport,
        freshness_report: str | Path | LambdaEvidenceFreshnessReport,
        blocker_matrix: str | Path | LambdaRealLaunchBlockerMatrix,
        m025_review: str | Path | LambdaFinalPrelaunchReviewReport,
    ) -> LambdaRealLaunchDecisionReport:
        human = _load_human(human_review_validation)
        freshness = _load_freshness(freshness_report)
        matrix = _load_matrix(blocker_matrix)
        review = _load_review(m025_review)
        blockers = [
            blocker.message
            for blocker in matrix.blockers
            if blocker.blocks_m027_implementation_authorization
        ]
        if review.go_no_go_recommendation != "go_for_future_m026_real_launch_review":
            blockers.append("M025 review did not recommend future M026 review")
        if not human.human_review_valid_for_m027_authorization:
            status: LambdaRealLaunchDecisionStatus = "needs_more_evidence"
            rationale = "Human review is incomplete or did not request M027 authorization."
        elif not freshness.freshness_passed:
            status = "needs_more_evidence"
            rationale = "Freshness evidence is stale or missing."
        elif blockers:
            status = "blocked"
            rationale = "M027 implementation authorization is blocked."
        else:
            status = "approve_m027_minimal_real_mutation_implementation"
            rationale = (
                "M026 authorizes only M027 minimal mutation implementation work; "
                "launch remains disabled."
            )
        record = LambdaRealLaunchDecisionRecord(
            status=status,
            rationale=rationale,
            blockers=blockers,
            warnings=[
                "M026 approval is implementation authorization only, not launch approval.",
                *matrix.warnings,
            ],
            next_required_steps=[
                "M027 may implement minimal mutation code disabled by default",
                "M028 or later must separately approve any real launch execution",
            ],
        )
        return LambdaRealLaunchDecisionReport(
            decision_record=record,
            human_review_valid=human.human_review_valid_for_m027_authorization,
            freshness_passed=freshness.freshness_passed,
            m027_authorization_blocked=matrix.m027_authorization_blocked,
            m025_review_recommendation=review.go_no_go_recommendation,
            warnings=record.warnings,
        )


def decide_lambda_real_launch(
    *,
    human_review_validation: str | Path | LambdaHumanReviewValidationReport,
    freshness_report: str | Path | LambdaEvidenceFreshnessReport,
    blocker_matrix: str | Path | LambdaRealLaunchBlockerMatrix,
    m025_review: str | Path | LambdaFinalPrelaunchReviewReport,
) -> LambdaRealLaunchDecisionReport:
    return LambdaRealLaunchDecisionGate().decide(
        human_review_validation=human_review_validation,
        freshness_report=freshness_report,
        blocker_matrix=blocker_matrix,
        m025_review=m025_review,
    )


def _load_human(value: str | Path | LambdaHumanReviewValidationReport):
    if isinstance(value, LambdaHumanReviewValidationReport):
        return value
    return load_lambda_human_review_validation_report(value)


def _load_freshness(value: str | Path | LambdaEvidenceFreshnessReport):
    if isinstance(value, LambdaEvidenceFreshnessReport):
        return value
    return load_lambda_evidence_freshness_report(value)


def _load_matrix(value: str | Path | LambdaRealLaunchBlockerMatrix):
    if isinstance(value, LambdaRealLaunchBlockerMatrix):
        return value
    return load_lambda_real_launch_blocker_matrix(value)


def _load_review(value: str | Path | LambdaFinalPrelaunchReviewReport):
    if isinstance(value, LambdaFinalPrelaunchReviewReport):
        return value
    return load_lambda_final_prelaunch_review(value)
