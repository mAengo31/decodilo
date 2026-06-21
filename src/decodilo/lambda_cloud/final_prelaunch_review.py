"""Final M025 pre-launch review gate for future first Lambda launch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.final_prelaunch_evidence_package import (
    LambdaFinalPrelaunchEvidencePackage,
    load_lambda_final_prelaunch_evidence_package,
)
from decodilo.lambda_cloud.first_launch_operator_checklist import (
    LambdaFirstLaunchOperatorChecklist,
    evaluate_lambda_first_launch_operator_checklist,
    load_lambda_first_launch_operator_checklist,
)
from decodilo.lambda_cloud.resource_ownership_review import LambdaResourceOwnershipReview
from decodilo.lambda_cloud.secret_handling_review import LambdaSecretHandlingReview
from decodilo.lambda_cloud.semantic_mutation_audit import (
    LambdaSemanticMutationAuditReport,
    load_lambda_semantic_mutation_audit_report,
)
from decodilo.lambda_cloud.spend_safety_review import LambdaSpendSafetyReview

LambdaGoNoGoRecommendation = Literal[
    "no_go",
    "go_for_future_m026_real_launch_review",
    "blocked",
]


class LambdaFinalPrelaunchReviewCriterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    criterion_id: str
    passed: bool
    blocker: bool = True
    message: str


class LambdaFinalPrelaunchReviewReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    review_id: str = "lambda-final-prelaunch-review-m025"
    criteria: list[LambdaFinalPrelaunchReviewCriterion]
    passed_criteria: list[str] = Field(default_factory=list)
    failed_criteria: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    future_first_launch_candidate: bool = False
    go_no_go_recommendation: LambdaGoNoGoRecommendation = "no_go"
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaFinalPrelaunchReviewReport:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M025 final review cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaFinalPrelaunchReview = LambdaFinalPrelaunchReviewReport


def build_lambda_final_prelaunch_review(
    *,
    evidence_package: str | Path | LambdaFinalPrelaunchEvidencePackage,
    operator_checklist: str | Path | LambdaFirstLaunchOperatorChecklist,
    semantic_audit: str | Path | LambdaSemanticMutationAuditReport,
    spend_safety_review: LambdaSpendSafetyReview | None = None,
    resource_ownership_review: LambdaResourceOwnershipReview | None = None,
    secret_handling_review: LambdaSecretHandlingReview | None = None,
) -> LambdaFinalPrelaunchReviewReport:
    package = _load_package(evidence_package)
    checklist = _load_checklist(operator_checklist)
    semantic = _load_semantic(semantic_audit)
    checklist_report = evaluate_lambda_first_launch_operator_checklist(checklist)
    criteria = [
        LambdaFinalPrelaunchReviewCriterion(
            criterion_id="evidence_package_complete",
            passed=package.evidence_complete,
            message="final evidence package complete",
        ),
        LambdaFinalPrelaunchReviewCriterion(
            criterion_id="semantic_mutation_audit_passed",
            passed=semantic.passed,
            message="semantic mutation audit passed",
        ),
        LambdaFinalPrelaunchReviewCriterion(
            criterion_id="operator_checklist_complete",
            passed=checklist_report.checklist_complete_for_review,
            message="operator checklist complete for review only",
        ),
        LambdaFinalPrelaunchReviewCriterion(
            criterion_id="spend_safety_review_passed",
            passed=spend_safety_review is None or spend_safety_review.spend_safety_passed,
            message="spend safety review passed",
        ),
        LambdaFinalPrelaunchReviewCriterion(
            criterion_id="resource_ownership_review_passed",
            passed=(
                resource_ownership_review is None
                or resource_ownership_review.resource_ownership_passed
            ),
            message="resource ownership review passed",
        ),
        LambdaFinalPrelaunchReviewCriterion(
            criterion_id="secret_handling_review_passed",
            passed=secret_handling_review is None or secret_handling_review.secret_handling_passed,
            message="secret handling review passed",
        ),
        LambdaFinalPrelaunchReviewCriterion(
            criterion_id="launch_disabled_current_build",
            passed=True,
            message="launch remains disabled in current build",
        ),
    ]
    blockers = [
        f"failed criterion: {criterion.criterion_id}"
        for criterion in criteria
        if not criterion.passed and criterion.blocker
    ]
    blockers.extend(package.blockers)
    blockers.extend(semantic.blockers)
    blockers.extend(checklist_report.blockers)
    if spend_safety_review is not None:
        blockers.extend(spend_safety_review.blockers)
    if resource_ownership_review is not None:
        blockers.extend(resource_ownership_review.blockers)
    if secret_handling_review is not None:
        blockers.extend(secret_handling_review.blockers)
    passed = [criterion.criterion_id for criterion in criteria if criterion.passed]
    failed = [criterion.criterion_id for criterion in criteria if not criterion.passed]
    recommendation: LambdaGoNoGoRecommendation = (
        "go_for_future_m026_real_launch_review" if not blockers else "blocked"
    )
    return LambdaFinalPrelaunchReviewReport(
        criteria=criteria,
        passed_criteria=passed,
        failed_criteria=failed,
        blockers=blockers,
        warnings=[
            "future launch review candidate only; launch remains disabled in this build",
            *package.warnings,
            *semantic.warnings,
            *checklist_report.warnings,
        ],
        future_first_launch_candidate=not blockers,
        go_no_go_recommendation=recommendation,
    )


def _load_package(
    value: str | Path | LambdaFinalPrelaunchEvidencePackage,
) -> LambdaFinalPrelaunchEvidencePackage:
    if isinstance(value, LambdaFinalPrelaunchEvidencePackage):
        return value
    return load_lambda_final_prelaunch_evidence_package(value)


def _load_checklist(
    value: str | Path | LambdaFirstLaunchOperatorChecklist,
) -> LambdaFirstLaunchOperatorChecklist:
    if isinstance(value, LambdaFirstLaunchOperatorChecklist):
        return value
    return load_lambda_first_launch_operator_checklist(value)


def _load_semantic(
    value: str | Path | LambdaSemanticMutationAuditReport,
) -> LambdaSemanticMutationAuditReport:
    if isinstance(value, LambdaSemanticMutationAuditReport):
        return value
    return load_lambda_semantic_mutation_audit_report(value)


def load_lambda_final_prelaunch_review(path: str | Path) -> LambdaFinalPrelaunchReviewReport:
    return LambdaFinalPrelaunchReviewReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_final_prelaunch_review(
    path: str | Path,
    report: LambdaFinalPrelaunchReviewReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
