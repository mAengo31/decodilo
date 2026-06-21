"""M037 decision record."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.endpoint_confidence_decision import (
    LambdaEndpointConfidenceDecision,
    load_lambda_endpoint_confidence_decision,
)
from decodilo.lambda_cloud.lower_cost_reauthorization_package import (
    LambdaLowerCostReauthorizationPackage,
    load_lambda_lower_cost_reauthorization_package,
)
from decodilo.lambda_cloud.lower_cost_shape_operator_selection import (
    LambdaLowerCostShapeOperatorSelection,
    load_lambda_lower_cost_shape_operator_selection,
)
from decodilo.lambda_cloud.support_response_evidence_package import (
    LambdaSupportResponseEvidencePackage,
    load_lambda_support_response_evidence_package,
)

LambdaM037DecisionStatus = Literal[
    "require_more_support_evidence",
    "endpoint_confirmed_reauthorize_lower_cost_shape",
    "endpoint_confirmed_keep_current_shape",
    "endpoint_contradiction_fix_implementation_first",
    "pause_launch_attempts",
]


class LambdaM037DecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_id: str = "lambda-m037-decision-record"
    status: LambdaM037DecisionStatus
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM037DecisionRecord:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M037 decision cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m037_decision_record(
    *,
    support_evidence_package: LambdaSupportResponseEvidencePackage | None = None,
    endpoint_decision: LambdaEndpointConfidenceDecision | None = None,
    shape_selection: LambdaLowerCostShapeOperatorSelection | None = None,
    reauthorization_package: LambdaLowerCostReauthorizationPackage | None = None,
) -> LambdaM037DecisionRecord:
    blockers: list[str] = []
    if support_evidence_package is None or not support_evidence_package.package_passed:
        blockers.extend(
            ["support_response_missing"]
            if support_evidence_package is None
            else support_evidence_package.blockers
        )
        return LambdaM037DecisionRecord(
            status="require_more_support_evidence",
            blockers=sorted(set(blockers)),
            warnings=["M037 cannot fabricate support/operator answers"],
        )
    if endpoint_decision is None:
        return LambdaM037DecisionRecord(
            status="require_more_support_evidence",
            blockers=["endpoint_confidence_decision_missing"],
        )
    if endpoint_decision.status == "endpoint_behavior_contradicts_current_implementation":
        return LambdaM037DecisionRecord(
            status="endpoint_contradiction_fix_implementation_first",
            blockers=endpoint_decision.blockers,
        )
    if endpoint_decision.status not in {
        "endpoint_confidence_high",
        "endpoint_confidence_medium_accepted",
    }:
        return LambdaM037DecisionRecord(
            status="require_more_support_evidence",
            blockers=endpoint_decision.blockers or ["endpoint_confidence_insufficient"],
        )
    if (
        shape_selection is not None
        and shape_selection.selection_status == "select_lower_cost_shape"
    ):
        return LambdaM037DecisionRecord(
            status="endpoint_confirmed_reauthorize_lower_cost_shape",
            blockers=(
                []
                if reauthorization_package is not None
                else ["reauthorization_package_missing"]
            ),
            warnings=["future lower-cost reauthorization required before launch"],
        )
    if shape_selection is not None and shape_selection.selection_status == "keep_current_shape":
        return LambdaM037DecisionRecord(status="endpoint_confirmed_keep_current_shape")
    return LambdaM037DecisionRecord(
        status="require_more_support_evidence",
        blockers=["shape_selection_incomplete"],
    )


def build_lambda_m037_decision_record_from_paths(
    *,
    support_evidence_package: str | Path | None = None,
    endpoint_decision: str | Path | None = None,
    shape_selection: str | Path | None = None,
    reauthorization_package: str | Path | None = None,
) -> LambdaM037DecisionRecord:
    return build_lambda_m037_decision_record(
        support_evidence_package=None
        if support_evidence_package is None
        else load_lambda_support_response_evidence_package(support_evidence_package),
        endpoint_decision=None
        if endpoint_decision is None
        else load_lambda_endpoint_confidence_decision(endpoint_decision),
        shape_selection=None
        if shape_selection is None
        else load_lambda_lower_cost_shape_operator_selection(shape_selection),
        reauthorization_package=None
        if reauthorization_package is None
        else load_lambda_lower_cost_reauthorization_package(reauthorization_package),
    )


def load_lambda_m037_decision_record(path: str | Path) -> LambdaM037DecisionRecord:
    return LambdaM037DecisionRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m037_decision_record(
    path: str | Path,
    record: LambdaM037DecisionRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")
