"""M036 endpoint confidence upgrade decision."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ambiguous_response_semantics import (
    LambdaAmbiguousResponseSemantics,
    load_lambda_ambiguous_response_semantics,
)
from decodilo.lambda_cloud.endpoint_behavior_evidence import (
    LambdaEndpointBehaviorEvidence,
    load_lambda_endpoint_behavior_evidence,
)
from decodilo.lambda_cloud.idempotency_semantics_evidence import (
    LambdaIdempotencySemanticsEvidence,
    load_lambda_idempotency_semantics_evidence,
)
from decodilo.lambda_cloud.launch_endpoint_confidence_review import (
    LambdaLaunchEndpointConfidenceReview,
    load_lambda_launch_endpoint_confidence_review,
)
from decodilo.lambda_cloud.response_shape_evidence import (
    LambdaResponseShapeEvidence,
    load_lambda_response_shape_evidence,
)
from decodilo.lambda_cloud.support_confirmation_validator import (
    LambdaSupportConfirmationValidationReport,
    load_lambda_support_confirmation_validation_report,
)


class LambdaEndpointConfidenceUpgradeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    previous_confidence: str = "medium"
    upgraded_confidence: str
    upgrade_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaEndpointConfidenceUpgradeReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("endpoint confidence upgrade cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_endpoint_confidence_upgrade(
    *,
    support_validation: LambdaSupportConfirmationValidationReport,
    endpoint_behavior: LambdaEndpointBehaviorEvidence | None = None,
    response_shape: LambdaResponseShapeEvidence | None = None,
    idempotency_semantics: LambdaIdempotencySemanticsEvidence | None = None,
    ambiguous_response_semantics: LambdaAmbiguousResponseSemantics | None = None,
    previous_review: LambdaLaunchEndpointConfidenceReview | None = None,
) -> LambdaEndpointConfidenceUpgradeReport:
    blockers = list(support_validation.blockers)
    if endpoint_behavior is None:
        blockers.append("endpoint_behavior_evidence_missing")
    elif endpoint_behavior.blockers:
        blockers.extend(endpoint_behavior.blockers)
    if response_shape is None:
        blockers.append("response_shape_evidence_missing")
    elif response_shape.blockers:
        blockers.extend(response_shape.blockers)
    if ambiguous_response_semantics is None:
        blockers.append("ambiguous_response_semantics_missing")
    elif ambiguous_response_semantics.blockers:
        blockers.extend(ambiguous_response_semantics.blockers)
    if idempotency_semantics is None:
        blockers.append("idempotency_semantics_missing")
    previous = "medium" if previous_review is None else previous_review.endpoint_confidence_current
    upgraded = (
        "high"
        if not blockers and support_validation.endpoint_confidence_candidate == "high"
        else previous
    )
    return LambdaEndpointConfidenceUpgradeReport(
        previous_confidence=previous,
        upgraded_confidence=upgraded,
        upgrade_passed=upgraded == "high",
        blockers=sorted(set(blockers)),
        warnings=[
            "confidence upgrade is review-only and does not authorize launch",
            *(ambiguous_response_semantics.warnings if ambiguous_response_semantics else []),
            *(idempotency_semantics.warnings if idempotency_semantics else []),
        ],
    )


def build_lambda_endpoint_confidence_upgrade_from_paths(
    *,
    validation: str | Path,
    endpoint_behavior: str | Path | None = None,
    response_shape: str | Path | None = None,
    idempotency_semantics: str | Path | None = None,
    ambiguous_response_semantics: str | Path | None = None,
    previous_review: str | Path | None = None,
) -> LambdaEndpointConfidenceUpgradeReport:
    return build_lambda_endpoint_confidence_upgrade(
        support_validation=load_lambda_support_confirmation_validation_report(validation),
        endpoint_behavior=None
        if endpoint_behavior is None
        else load_lambda_endpoint_behavior_evidence(endpoint_behavior),
        response_shape=None
        if response_shape is None
        else load_lambda_response_shape_evidence(response_shape),
        idempotency_semantics=None
        if idempotency_semantics is None
        else load_lambda_idempotency_semantics_evidence(idempotency_semantics),
        ambiguous_response_semantics=None
        if ambiguous_response_semantics is None
        else load_lambda_ambiguous_response_semantics(ambiguous_response_semantics),
        previous_review=None
        if previous_review is None
        else load_lambda_launch_endpoint_confidence_review(previous_review),
    )


def load_lambda_endpoint_confidence_upgrade_report(
    path: str | Path,
) -> LambdaEndpointConfidenceUpgradeReport:
    return LambdaEndpointConfidenceUpgradeReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_endpoint_confidence_upgrade_report(
    path: str | Path,
    report: LambdaEndpointConfidenceUpgradeReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
