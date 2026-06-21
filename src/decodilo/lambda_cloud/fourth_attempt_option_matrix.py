"""M035 fourth-attempt option matrix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.fourth_attempt_risk_review import (
    LambdaFourthAttemptRiskReview,
    build_lambda_fourth_attempt_risk_review,
)
from decodilo.lambda_cloud.launch_attempt_history import (
    LambdaLaunchAttemptHistoryReport,
    load_lambda_launch_attempt_history_report,
)
from decodilo.lambda_cloud.launch_endpoint_confidence_review import (
    LambdaLaunchEndpointConfidenceReview,
    load_lambda_launch_endpoint_confidence_review,
)
from decodilo.lambda_cloud.launch_shape_strategy_review import (
    LambdaLaunchShapeStrategyReview,
    load_lambda_launch_shape_strategy_review,
)

LambdaFourthAttemptOption = Literal[
    "no_go_pause_launches",
    "require_lambda_support_confirmation",
    "attempt_fourth_with_same_shape_and_crash_safe_diagnostics",
    "attempt_fourth_with_lower_cost_shape",
    "run_additional_fake_endpoint_diagnostics",
    "adjust_timeout_capture_only",
]


class LambdaFourthAttemptOptionItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    option: LambdaFourthAttemptOption
    expected_benefit: str
    residual_risk: str
    estimated_maximum_spend: float
    evidence_required: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    recommendation_score: int
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaFourthAttemptOptionItem:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M035 option item cannot enable launch")
        return self


class LambdaFourthAttemptOptionMatrix(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    options: list[LambdaFourthAttemptOptionItem]
    recommended_option: LambdaFourthAttemptOption
    endpoint_support_confirmation_required: bool
    lower_cost_shape_reauthorization_required: bool
    risk_review: LambdaFourthAttemptRiskReview
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaFourthAttemptOptionMatrix:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M035 option matrix cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_fourth_attempt_option_matrix(
    *,
    attempt_history: LambdaLaunchAttemptHistoryReport,
    endpoint_confidence: LambdaLaunchEndpointConfidenceReview,
    shape_strategy: LambdaLaunchShapeStrategyReview,
    operator_accepts_medium_endpoint_risk: bool = False,
    operator_prefers_current_shape: bool = False,
) -> LambdaFourthAttemptOptionMatrix:
    risk = build_lambda_fourth_attempt_risk_review(
        attempt_history=attempt_history,
        endpoint_confidence=endpoint_confidence,
    )
    support_required = endpoint_confidence.support_or_docs_confirmation_required
    lower_cost_required = (
        shape_strategy.recommended_shape_strategy == "switch_to_lower_cost_shape"
        and not operator_prefers_current_shape
    )
    options = [
        LambdaFourthAttemptOptionItem(
            option="no_go_pause_launches",
            expected_benefit="eliminates further billable ambiguity",
            residual_risk="low",
            estimated_maximum_spend=0.0,
            evidence_required=[],
            blockers=[],
            recommendation_score=70,
        ),
        LambdaFourthAttemptOptionItem(
            option="require_lambda_support_confirmation",
            expected_benefit="raises endpoint confidence before another mutation",
            residual_risk="medium",
            estimated_maximum_spend=0.0,
            evidence_required=[
                "provider or operator confirms launch endpoint path/method",
                "provider or operator confirms launch response schema",
            ],
            blockers=[],
            recommendation_score=95 if support_required else 50,
        ),
        LambdaFourthAttemptOptionItem(
            option="attempt_fourth_with_same_shape_and_crash_safe_diagnostics",
            expected_benefit="tests crash-safe diagnostics on the current launch shape",
            residual_risk="high",
            estimated_maximum_spend=50.0,
            evidence_required=[
                "fresh read-only discovery",
                "operator confirmation",
                "explicit risk acceptance",
            ],
            blockers=[]
            if operator_accepts_medium_endpoint_risk and not lower_cost_required
            else ["endpoint_or_shape_risk_not_accepted"],
            recommendation_score=60 if operator_accepts_medium_endpoint_risk else 20,
        ),
        LambdaFourthAttemptOptionItem(
            option="attempt_fourth_with_lower_cost_shape",
            expected_benefit="reduces spend exposure for lifecycle-only smoke",
            residual_risk="medium-high",
            estimated_maximum_spend=50.0,
            evidence_required=[
                "updated product catalog and non-sample price evidence",
                "updated M020/M028/M029 authorization artifacts",
            ],
            blockers=[]
            if lower_cost_required
            else ["lower_cost_shape_not_available_or_not_selected"],
            recommendation_score=90 if lower_cost_required and not support_required else 65,
        ),
        LambdaFourthAttemptOptionItem(
            option="run_additional_fake_endpoint_diagnostics",
            expected_benefit="covers parser/transport edge cases without spend",
            residual_risk="low",
            estimated_maximum_spend=0.0,
            evidence_required=["redacted response fixtures if available"],
            blockers=[],
            recommendation_score=75,
        ),
        LambdaFourthAttemptOptionItem(
            option="adjust_timeout_capture_only",
            expected_benefit=(
                "keeps instrumentation current but does not resolve endpoint uncertainty"
            ),
            residual_risk="medium",
            estimated_maximum_spend=0.0,
            evidence_required=["updated crash-safe diagnostic validation"],
            blockers=[],
            recommendation_score=45,
        ),
    ]
    recommended: LambdaFourthAttemptOption
    if support_required and not operator_accepts_medium_endpoint_risk:
        recommended = "require_lambda_support_confirmation"
    elif lower_cost_required:
        recommended = "attempt_fourth_with_lower_cost_shape"
    elif operator_accepts_medium_endpoint_risk:
        recommended = "attempt_fourth_with_same_shape_and_crash_safe_diagnostics"
    else:
        recommended = "no_go_pause_launches"
    return LambdaFourthAttemptOptionMatrix(
        options=options,
        recommended_option=recommended,
        endpoint_support_confirmation_required=support_required,
        lower_cost_shape_reauthorization_required=lower_cost_required,
        risk_review=risk,
        warnings=[
            "M035 option matrix is review-only and cannot authorize execution",
            *endpoint_confidence.confidence_warnings,
            *shape_strategy.warnings,
        ],
    )


def build_lambda_fourth_attempt_option_matrix_from_paths(
    *,
    attempt_history: str | Path,
    endpoint_confidence: str | Path,
    shape_strategy: str | Path,
) -> LambdaFourthAttemptOptionMatrix:
    return build_lambda_fourth_attempt_option_matrix(
        attempt_history=load_lambda_launch_attempt_history_report(attempt_history),
        endpoint_confidence=load_lambda_launch_endpoint_confidence_review(
            endpoint_confidence
        ),
        shape_strategy=load_lambda_launch_shape_strategy_review(shape_strategy),
    )


def load_lambda_fourth_attempt_option_matrix(
    path: str | Path,
) -> LambdaFourthAttemptOptionMatrix:
    return LambdaFourthAttemptOptionMatrix.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_fourth_attempt_option_matrix(
    path: str | Path,
    report: LambdaFourthAttemptOptionMatrix,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
