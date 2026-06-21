"""M036 combined support confirmation and lower-cost reauthorization report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.endpoint_confidence_upgrade import (
    LambdaEndpointConfidenceUpgradeReport,
    load_lambda_endpoint_confidence_upgrade_report,
)
from decodilo.lambda_cloud.lower_cost_shape_reauthorization import (
    LambdaLowerCostShapeReauthorization,
    load_lambda_lower_cost_shape_reauthorization,
)
from decodilo.lambda_cloud.m036_strategy_decision import (
    LambdaM036StrategyDecision,
    build_lambda_m036_missing_support_decision,
    load_lambda_m036_strategy_decision,
)
from decodilo.lambda_cloud.support_confirmation_request import (
    LambdaSupportConfirmationRequestReport,
    load_lambda_support_confirmation_request_report,
)
from decodilo.lambda_cloud.support_confirmation_response import (
    LambdaSupportConfirmationResponse,
    load_lambda_support_confirmation_response,
)
from decodilo.lambda_cloud.support_confirmation_validator import (
    LambdaSupportConfirmationValidationReport,
    load_lambda_support_confirmation_validation_report,
)


class LambdaM036Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_id: str = "lambda-m036-support-confirmation-and-shape-reauthorization"
    support_request: LambdaSupportConfirmationRequestReport
    support_response: LambdaSupportConfirmationResponse | None = None
    validation: LambdaSupportConfirmationValidationReport | None = None
    endpoint_confidence_upgrade: LambdaEndpointConfidenceUpgradeReport | None = None
    lower_cost_shape_review: LambdaLowerCostShapeReauthorization
    strategy_decision: LambdaM036StrategyDecision
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM036Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M036 report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m036_report(
    *,
    support_request: LambdaSupportConfirmationRequestReport,
    lower_cost_shape_review: LambdaLowerCostShapeReauthorization,
    strategy_decision: LambdaM036StrategyDecision | None = None,
    support_response: LambdaSupportConfirmationResponse | None = None,
    validation: LambdaSupportConfirmationValidationReport | None = None,
    endpoint_confidence_upgrade: LambdaEndpointConfidenceUpgradeReport | None = None,
) -> LambdaM036Report:
    effective_decision = (
        build_lambda_m036_missing_support_decision()
        if strategy_decision is None
        else strategy_decision
    )
    blockers = [
        *lower_cost_shape_review.blockers,
        *effective_decision.blockers,
    ]
    if support_response is None:
        blockers.append("support_confirmation_response_missing")
    if validation is not None and not validation.validation_passed:
        blockers.extend(validation.blockers)
    if endpoint_confidence_upgrade is not None and not endpoint_confidence_upgrade.upgrade_passed:
        blockers.extend(endpoint_confidence_upgrade.blockers)
    return LambdaM036Report(
        support_request=support_request,
        support_response=support_response,
        validation=validation,
        endpoint_confidence_upgrade=endpoint_confidence_upgrade,
        lower_cost_shape_review=lower_cost_shape_review,
        strategy_decision=effective_decision,
        report_passed=support_request.required_question_count > 0
        and lower_cost_shape_review.decision.status
        in {"reauthorize_lower_cost_shape", "keep_current_shape", "needs_operator_selection"}
        and effective_decision.status
        in {
            "require_more_support_evidence",
            "reauthorize_lower_cost_shape_before_next_launch",
            "endpoint_confirmed_proceed_to_reauthorization",
            "keep_current_shape_with_operator_risk_acceptance",
            "pause_real_launch_attempts",
        },
        blockers=sorted(set(blockers)),
        warnings=[
            "M036 report is review-only and cannot authorize launch",
            *(validation.warnings if validation else []),
            *(endpoint_confidence_upgrade.warnings if endpoint_confidence_upgrade else []),
            *effective_decision.warnings,
        ],
    )


def build_lambda_m036_report_from_paths(
    *,
    support_request: str | Path,
    lower_cost_shape_review: str | Path,
    strategy_decision: str | Path | None = None,
    support_response: str | Path | None = None,
    validation: str | Path | None = None,
    endpoint_confidence_upgrade: str | Path | None = None,
) -> LambdaM036Report:
    return build_lambda_m036_report(
        support_request=load_lambda_support_confirmation_request_report(support_request),
        support_response=None
        if support_response is None
        else load_lambda_support_confirmation_response(support_response),
        validation=None
        if validation is None
        else load_lambda_support_confirmation_validation_report(validation),
        endpoint_confidence_upgrade=None
        if endpoint_confidence_upgrade is None
        else load_lambda_endpoint_confidence_upgrade_report(endpoint_confidence_upgrade),
        lower_cost_shape_review=load_lambda_lower_cost_shape_reauthorization(
            lower_cost_shape_review
        ),
        strategy_decision=None
        if strategy_decision is None
        else load_lambda_m036_strategy_decision(strategy_decision),
    )


def load_lambda_m036_report(path: str | Path) -> LambdaM036Report:
    return LambdaM036Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m036_report(path: str | Path, report: LambdaM036Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
